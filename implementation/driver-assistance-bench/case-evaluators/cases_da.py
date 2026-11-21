"""The S1 case evaluators of INC-DRIVING-002: VC-DRIVING-036 to -038 and -040 to -044.

Pattern: the INC-DRIVING-001 frame (`implementation/closed-loop-driving-bench/case-evaluators/cases.py:236-316`:
a `Result` per case, `ok`/`bad`/`inconclusive`, a registry of `@case` evaluators). Each case judges every run it
reads (a run entry with its own outcome, measured values and missing-evidence texts), then combines the runs by the
campaign rule (OBSERVABLES.md, "Outcomes"). The outcome literals are the six of `AssistanceEvidenceOutcome`
(`driver_assistance_verification_evidence.sysml:144-162`), the verdict that of `MapAssistanceEvidenceOutcomeToVerdict`
(`:164-172`).
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
    "VC-DRIVING-036": ("REQ-DRIVING-036", f"{NR}:286"),
    "VC-DRIVING-037": ("REQ-DRIVING-037", f"{NR}:296"),
    "VC-DRIVING-038": ("REQ-DRIVING-038", f"{NR}:306"),
    "VC-DRIVING-040": ("REQ-DRIVING-040", f"{NR}:326"),
    "VC-DRIVING-041": ("REQ-DRIVING-041", f"{NR}:336"),
    "VC-DRIVING-042": ("REQ-DRIVING-042", f"{NR}:346"),
    "VC-DRIVING-043": ("REQ-DRIVING-043", f"{NR}:356"),
    "VC-DRIVING-044": ("REQ-DRIVING-044", f"{NR}:366"),
}
DROP_RULE = "MAP-DRIVING-DA-CAMERA-IMAGE; driver_assistance_verification_evidence.sysml:228-231"


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


class DroppedImage(MissingEvidence):
    """A dropped image inside the judged window (the dropped-image rule)."""


_IGNORE_DROPS = [False]


def _reading_without_drop_rule(fn, run: Run, *args) -> dict:
    """What the criterion reads on the run when the dropped-image rule is set aside: a measured value for the
    diagnosis of a run that the rule leaves inconclusive, never its outcome."""
    _IGNORE_DROPS[0] = True
    try:
        e = fn(run, *args)
        return {"outcome": e["outcome"], "measured": e["measured"], "missing": e["missing"], "notes": e["notes"]}
    except MissingEvidence as exc:
        return {"outcome": INCONCLUSIVE, "measured": {}, "missing": [str(exc)], "notes": []}
    except EvidenceError as exc:
        return {"outcome": ERROR, "measured": {}, "missing": [str(exc)], "notes": []}
    finally:
        _IGNORE_DROPS[0] = False


def guarded(fn, run: Run, *args) -> dict:
    """One run through a per-run evaluator: missing evidence and unreadable records become its outcome."""
    try:
        return fn(run, *args)
    except DroppedImage as exc:
        return entry(run, INCONCLUSIVE, missing=[str(exc)],
                     measured={"withoutDropRule": _reading_without_drop_rule(fn, run, *args)})
    except MissingEvidence as exc:
        return entry(run, INCONCLUSIVE, missing=[str(exc)])
    except EvidenceError as exc:
        return entry(run, ERROR, missing=[str(exc)])


def no_drop_in(run: Run, w0: float, w1: float) -> None:
    if _IGNORE_DROPS[0]:
        return
    drops = run.drops_in(w0, w1)
    if drops:
        shown = ", ".join(f"{d['sim_s']:.3f}" for d in drops[:5]) + (" ..." if len(drops) > 5 else "")
        raise DroppedImage(f"{run.label('score')}: {len(drops)} drop.camera_image at sim {shown} s inside the "
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


# ------------------------------------------------------------------ every-run cases
def every_run_campaign(vc: str, sess: Session, per_run, settings: tuple, thresholds: dict,
                       stop_clause=None, extra=None) -> dict:
    """038, 040, 041, 043, 044: every run of the named settings (two each) meets the criterion; a missing run or a
    run with a dropped image gives inconclusive, never pass. The stop clause of 038 and 043 reads the stop run."""
    by = sess.by_setting()
    runs, missing = [], []
    for sid in settings:
        have = by.get(sid, [])
        if len(have) != 2:
            missing.append(f"setting {sid}: {len(have)} run{'' if len(have) == 1 else 's'} of 2")
        entries = [guarded(per_run, r) for r in have]
        runs += entries
        for e in entries:
            if e["outcome"] not in (PASS, FAIL):
                missing.append(f"run {e['run']} ({sid}): " + "; ".join(e["missing"]))
    outcomes = [e["outcome"] for e in runs]
    measured: dict = {}
    if stop_clause is not None:
        sc = stop_clause(sess)
        measured["stopClause"] = sc
        outcomes.append(sc["outcome"])
        missing += [f"stop clause: {m}" for m in sc["missing"]]
    notes: list = []
    if extra is not None:
        ex = extra(sess, runs)
        measured.update(ex.get("measured", {}))
        # the outcomes of the clauses that no run shows (044's desk reproduction), kept for the campaign's rule on
        # partial run records (evaluate_da_campaign.py)
        measured["outcomesWithoutRun"] = list(ex.get("outcomes", []))
        outcomes += ex.get("outcomes", [])
        missing += ex.get("missing", [])
        notes += ex.get("notes", [])
    return result(vc, combine(outcomes, missing), runs, missing, thresholds, notes=notes, measured=measured)


def _setting_terms(run: Run) -> terms.SettingTerms:
    st = terms.SETTINGS.get(run.setting_id)
    if st is None:
        raise MissingEvidence(f"run {run.run_id}: unknown setting {run.setting_id!r}")
    return st


# The speeds and the times to collision that the source's guidance names for SC-DRIVING-014 and -015 and that the record
# holds (driver_assistance_verification_evidence.sysml:1168-1170), under the keys of world-side/sites.py GUIDANCE_014
# and GUIDANCE_015 (b9938fe9): setting_record.json["site"] = SiteSpec.as_record() (lead contract 1 of 2026-11-20)
GUIDANCE_KEYS = {
    "SC-DRIVING-014": ("approachKmh", "atCurveEntryMinKmh", "ttcAtTurnInMaxS", "inCurveMinKmh", "ttcAtOverlapZeroMaxS"),
    "SC-DRIVING-015": ("bothKmh", "targetTurnKmh", "egoAtTurnBeginMinKmh", "ttcAtTurnBeginMaxS", "egoAfterMinKmh",
                       "ttcAtOverlapZeroMaxS"),
}


def site_guidance(run: Run, scenario: str) -> dict:
    site = run.setting_record().get("site")
    guidance = site.get("guidance") if isinstance(site, dict) else None
    guidance = guidance if isinstance(guidance, dict) else {}
    absent = [k for k in GUIDANCE_KEYS[scenario] if guidance.get(k) is None]
    if absent:
        raise MissingEvidence(f"{run.label('setting_record')} site.guidance {', '.join(absent)}: the speeds and times "
                              f"to collision of the source's guidance for {scenario} that the record holds "
                              "(driver_assistance_verification_evidence.sysml:1168-1170; SiteSpec.as_record(), "
                              "world-side/sites.py)")
    return guidance


def starts_at_imminence(run: Run, starts: list[dict]) -> dict:
    """040 and 041: each start falls on a tick with a vehicle ahead in the lane to which a collision is imminent."""
    st = _setting_terms(run)
    whole_run(run)
    measured: dict = {"starts": len(starts), "startsAtImminent": 0, "firstStartNotImminent": None}
    if st.scenario in GUIDANCE_KEYS:
        measured["guidance"] = site_guidance(run, st.scenario)
    ticks = run.ticks()
    bad = []
    for s in starts:
        i = run.tick_of(s, "issueTime_sim_s")
        if i is None:
            raise MissingEvidence(f"{run.label('world')}: no tick at or before the start at sim "
                                  f"{s['issueTime_sim_s']:.3f} s")
        tick = ticks[i]
        va = tick.get("vehiclesAhead")
        if va is None:
            raise MissingEvidence(f"{run.label('world')} tick frame {tick.get('frame')} data.vehiclesAhead "
                                  "(shared contract 1, lane A6)")
        if not isinstance(va, list) or not all(isinstance(v, dict) for v in va):
            raise EvidenceError(f"{run.label('world')} tick frame {tick.get('frame')}: vehiclesAhead is not a "
                                "list of objects")
        hits = [v for v in va if v.get("inLane") is True and terms.is_imminent(v.get("gapM"), v.get("closingMps"))]
        if hits:
            measured["startsAtImminent"] += 1
        else:
            bad.append({"frame": tick.get("frame"), "simTimeS": tick["simTimeS"],
                        "scenarioTimeS": tick.get("scenarioTimeS"),
                        "vehiclesAhead": [{k: v.get(k) for k in ("actorId", "role", "gapM", "closingMps", "inLane")}
                                          for v in va]})
    measured["firstStartNotImminent"] = bad[0] if bad else None
    return entry(run, FAIL if bad else PASS, measured)


def run_040(run: Run) -> dict:
    return starts_at_imminence(run, terms.warning_starts(run.warnings()))


def run_041(run: Run) -> dict:
    return starts_at_imminence(run, terms.emergency_braking_starts(run.commands()))


def _crc(value) -> int | None:
    try:
        return int(str(value), 16)
    except ValueError:
        return None


def run_038(run: Run) -> dict:
    whole_run(run)
    statement = run.setting_record().get("controlOfTheHero")
    if not isinstance(statement, str) or not statement:
        raise MissingEvidence(f"{run.label('setting_record')} controlOfTheHero: the world's statement that no "
                              "autopilot and no Traffic Manager controls the vehicle (da_world_side.py:725-726)")
    ticks = run.ticks()
    if any(not isinstance(t.get("worldSideControlCalls"), int) for t in ticks):
        raise MissingEvidence(f"{run.label('world')}: a tick without worldSideControlCalls")
    wsc = max(t["worldSideControlCalls"] for t in ticks)
    s_crc = {c["seq"]: _crc(c.get("crc")) for c in run.commands()}
    a_in: dict = {}
    for line in run.adapter("in.driving_command"):
        d = line.get("data") or {}
        if d.get("crc_ok") is True and isinstance(d.get("seq"), int):
            a_in[d["seq"]] = d.get("checkValue")
    outs = run.adapter("out.ackermann_control")
    if not outs:
        raise MissingEvidence(f"{run.label('adapter')}: no out.ackermann_control")
    unmatched = []
    for line in outs:
        d = line.get("data") or {}
        seq = d.get("seq")
        ok = d.get("controlSource") == "actuationAdapter" and seq in a_in and seq in s_crc \
            and s_crc[seq] is not None and s_crc[seq] == a_in[seq]
        if not ok:
            unmatched.append({"seq": seq, "frame": d.get("frame"), "controlSource": d.get("controlSource"),
                              "adapterCheckValue": a_in.get(seq), "scoreCrc": s_crc.get(seq)})
    measured = {"actuations": len(outs), "matched": len(outs) - len(unmatched), "unmatched": unmatched[:10],
                "worldSideControlCallsMax": wsc, "controlOfTheHero": statement}
    return entry(run, FAIL if unmatched or wsc > 0 else PASS, measured)


def _stop_context(sess: Session, vc: str):
    run = sess.stop_run
    if run is None:
        raise MissingEvidence("the stop run: no run (run id stop, setting stop: lead contract 2; the further run of "
                              "SC-DRIVING-012 in which the S-CORE path is stopped)")
    rec = run.stop_record(sess.session)
    mono, real, rc = rec.get("stopInstantMonoNs"), rec.get("stopInstantRealNs"), rec.get("rc")
    if not isinstance(rc, int) or not isinstance(mono, int) or not isinstance(real, int):
        raise EvidenceError(f"the stop record of run {run.run_id}: rc, stopInstantMonoNs and stopInstantRealNs "
                            f"must be integers: {rec}")
    return run, rec


def _stop_entry(sess: Session, vc: str, fn) -> dict:
    run = sess.stop_run
    try:
        run, rec = _stop_context(sess, vc)
        if rec["rc"] != 0:
            return {"run": run.run_id, "outcome": BLOCKED, "measured": {"stopRecord": rec},
                    "missing": [f"path_stop of run {run.run_id} returned rc {rec['rc']}: the bench could not stop "
                                "the path"], "notes": []}
        whole_run(run)
        outcome, measured, *notes = fn(run, rec)
        measured["stopRecord"] = rec
        return {"run": run.run_id, "outcome": outcome, "measured": measured, "missing": [],
                "notes": notes[0] if notes else []}
    except MissingEvidence as exc:
        return {"run": getattr(run, "run_id", None), "outcome": INCONCLUSIVE, "measured": {}, "missing": [str(exc)],
                "notes": []}
    except EvidenceError as exc:
        return {"run": getattr(run, "run_id", None), "outcome": ERROR, "measured": {}, "missing": [str(exc)],
                "notes": []}


CONTROL_CHANGE_NOTE = (
    "controlChangesAfterStop is a note, not the criterion: a tick's control is hero.get_control(), the throttle, steer "
    "and brake that the simulator's Ackermann controller computes on every physics step, which changes under a held "
    "target with no command (closure review of 44a4be29..86cadee0, R1). The clause judges what reaches the actuation: "
    "the actuation adapter's out.ackermann_control after the stop instant and the world side's control calls on the "
    "vehicle after the stop (worldSideControlCalls)")


def stop_038(sess: Session) -> dict:
    """The stop clause of REQ-DRIVING-038: "in one further run of SC-DRIVING-012 in which the Eclipse S-CORE path of
    the driver-assistance system is stopped, no driving command reaches the actuation after the stop"
    (driver_assistance_needs_requirements.sysml:306; processData of VC-DRIVING-038,
    driver_assistance_verification_evidence.sysml:1100-1101). A driving command reaches the actuation of the vehicle
    by the actuation adapter (A out.ackermann_control) or by a control call of the world side (W
    worldSideControlCalls); either after the stop gives fail."""
    def fn(run: Run, rec: dict):
        stop = rec["stopInstantMonoNs"]
        outs = run.adapter("out.ackermann_control")
        after = [o for o in outs if isinstance(o.get("t_mono_ns"), int) and o["t_mono_ns"] > stop]
        before = [(o.get("data") or {}).get("frame") for o in outs
                  if isinstance(o.get("t_mono_ns"), int) and o["t_mono_ns"] <= stop]
        before = [f for f in before if isinstance(f, int)]
        last = max(before) if before else None
        all_ticks = run.ticks()
        ticks = [t for t in all_ticks if last is None or (isinstance(t.get("frame"), int) and t["frame"] > last)]
        if not ticks:
            raise MissingEvidence(f"{run.label('world')}: no tick after the last control applied before the stop")
        if any(not isinstance(t.get("worldSideControlCalls"), int) for t in ticks):
            raise MissingEvidence(f"{run.label('world')}: a tick after the stop without worldSideControlCalls")
        # worldSideControlCalls counts the world side's calls since the run began (da_world_side.py:1302): the calls
        # after the stop are its rise over the last tick up to the last control applied before the stop
        upto = [t for t in all_ticks if last is not None and isinstance(t.get("frame"), int) and t["frame"] <= last
                and isinstance(t.get("worldSideControlCalls"), int)]
        base = upto[-1]["worldSideControlCalls"] if upto else 0
        calls_after = max(0, max(t["worldSideControlCalls"] for t in ticks) - base)
        controls = [t["control"] for t in ticks if isinstance(t.get("control"), dict)]
        changes = sum(1 for c in controls if c != controls[0])
        measured = {"controlsAfterStop": len(after), "worldSideControlCallsAfterStop": calls_after,
                    "controlChangesAfterStop": changes, "lastControlFrameBeforeStop": last,
                    "ticksAfterStop": len(ticks)}
        return (FAIL if after or calls_after else PASS), measured, [CONTROL_CHANGE_NOTE]
    return _stop_entry(sess, "VC-DRIVING-038", fn)


def _receipt_bytes(r: dict) -> str | None:
    req, ms = r.get("requested"), r.get("issue_time_sim_ms")
    if not isinstance(req, int) or isinstance(req, bool) or not isinstance(ms, int) or req not in (0, 1) \
            or not 0 <= ms < 2 ** 32:
        return None
    return f"{req:08x}{ms:08x}"


def run_receipts(run: Run) -> list[dict]:
    """The receipts of one run: issue time in the run's sim span, or IVI real time (less the clock offset) in the
    run's wall span on the S-CORE host (its S start line to its last line)."""
    w0, w1 = run.run_span()
    reals = [x.get("real_ns") for x in run.score("start") + run.commands() if isinstance(x.get("real_ns"), int)]
    try:
        offset_ns = int(float(run.clock().get("offset_s", 0.0)) * 1e9)
    except MissingEvidence:
        offset_ns = 0
    lo, hi = (min(reals), max(reals)) if reals else (None, None)
    out = []
    for r in run.receipts():
        ms = r.get("issue_time_sim_ms")
        in_sim = isinstance(ms, int) and w0 * 1000.0 - 1.0 <= ms <= w1 * 1000.0 + 1.0
        t = r.get("t_real_ns")
        in_wall = lo is not None and isinstance(t, int) and lo <= t - offset_ns <= hi
        if in_sim or in_wall:
            out.append(r)
    return out


def run_043(run: Run) -> dict:
    whole_run(run)
    sent = {w.get("bytes") for w in run.warnings() if w.get("sent") is True}
    receipts = run_receipts(run)
    unmatched = [r for r in receipts if _receipt_bytes(r) not in sent]
    measured = {"receipts": len(receipts), "matched": len(receipts) - len(unmatched),
                "unmatched": [{k: r.get(k) for k in ("seq", "requested", "issue_time_sim_ms", "t_real_ns")}
                              for r in unmatched[:10]]}
    notes = [] if receipts else ["no receipt in the run: nothing reached the AAOS SDV"]
    return entry(run, FAIL if unmatched else PASS, measured, notes=notes)


def stop_043(sess: Session) -> dict:
    def fn(run: Run, rec: dict):
        images = [i for i in run.score("in.camera_image")
                  if isinstance(i.get("mono_ns"), int) and i["mono_ns"] <= rec["stopInstantMonoNs"]
                  and isinstance(i.get("sim_s"), (int, float))]
        if not images:
            raise MissingEvidence(f"{run.label('score')}: no in.camera_image before the stop instant")
        stop_sim = max(i["sim_s"] for i in images)
        receipts = run.receipts()
        after_sim = [r for r in receipts if isinstance(r.get("issue_time_sim_ms"), int)
                     and r["issue_time_sim_ms"] > stop_sim * 1000.0 + 1.0]
        notes, after_wall = [], []
        try:
            clk = run.clock()
            offset_ns, bound_ns = int(float(clk["offset_s"]) * 1e9), int(float(clk["bound_s"]) * 1e9)
            after_wall = [r for r in receipts if isinstance(r.get("t_real_ns"), int)
                          and r["t_real_ns"] - offset_ns > rec["stopInstantRealNs"] + bound_ns]
        except (MissingEvidence, KeyError, TypeError, ValueError):
            notes.append("no IVI clock mark: only the sim-time check ran")
        measured = {"stopSimS": stop_sim, "receiptsAfterStop": len({id(r) for r in after_sim + after_wall}),
                    "receiptsIssuedAfterStop": len(after_sim), "receiptsReadAfterStop": len(after_wall),
                    "notes": notes}
        return (FAIL if after_sim or after_wall else PASS), measured
    return _stop_entry(sess, "VC-DRIVING-043", fn)


def run_044(run: Run) -> dict:
    whole_run(run)
    cmds = run.commands()
    if not cmds:
        raise MissingEvidence(f"{run.label('score')}: no out.driving_command")
    firsts = [c for c in cmds if isinstance(c.get("mono_ns"), int)]
    if not firsts:
        raise MissingEvidence(f"{run.label('score')}: no out.driving_command with mono_ns")
    first = min(firsts, key=lambda c: c["mono_ns"])
    records = [r for r in run.score("in.candidate_record") if r.get("accepted") is True]
    measured: dict = {"firstCommandSeq": first["seq"], "recordBeforeFirstCommandNs": None, "recordSha256": None,
                      "diffBytes": None}
    if not records or not isinstance(records[0].get("mono_ns"), int):
        return entry(run, FAIL, measured, notes=["no accepted in.candidate_record with mono_ns in the run"])
    rec = min(records, key=lambda r: r["mono_ns"])
    measured.update(recordBeforeFirstCommandNs=first["mono_ns"] - rec["mono_ns"], recordSha256=rec.get("recordSha256"),
                    upstreamRevision=rec.get("upstreamRevision"), diffBytes=rec.get("diffBytes"))
    if not isinstance(rec.get("diffBytes"), int):
        raise MissingEvidence(f"{run.label('score')}: in.candidate_record without diffBytes")
    bad = measured["recordBeforeFirstCommandNs"] <= 0 or rec["diffBytes"] <= 0
    return entry(run, FAIL if bad else PASS, measured)


def desk_044(sess: Session, runs: list, desk: dict | None) -> dict:
    """The clauses that no run shows: another engineer re-derives the values (plan lane F2)."""
    d = (desk or {}).get("VC-DRIVING-044")
    if not isinstance(d, dict):
        return {"missing": ["reproduction_044.json: the desk reproduction by another engineer who checks out the "
                            "named revision, applies the recorded difference and hashes the named files "
                            "(needs_requirements.sysml:366; plan lane F2)"]}
    out: dict = {"measured": {"desk": d}, "outcomes": [], "missing": []}
    if not isinstance(d.get("engineer"), str) or not d["engineer"]:
        out["missing"].append("reproduction_044.json: no engineer")
    if d.get("valuesMatch") is False:
        out["outcomes"].append(FAIL)
    elif d.get("valuesMatch") is not True:
        out["missing"].append("reproduction_044.json: valuesMatch is not true or false")
    shas = set(d.get("recordSha256") or [])
    for e in runs:
        sha = (e.get("measured") or {}).get("recordSha256")
        if sha and sha not in shas:
            out["missing"].append(f"run {e['run']}: record {sha} not reproduced in reproduction_044.json")
    return out


THRESHOLDS = {
    "VC-DRIVING-036": {"neededDecelMps2AtLeast": 5.0, "commandAccelerationAtMost": -5.0},
    "VC-DRIVING-037": {"maxRelativeImpactKmh": [list(x) for x in terms.IMPACT_LIMITS_KMH],
                       "imminent": {"ttcSAtMost": 4.0, "neededDecelMps2AtLeast": 1.0}},
    "VC-DRIVING-042": {"warningLeadSAtLeast": 1.0, "emergencyBrakingMps2": 5.0,
                       "imminent": {"ttcSAtMost": 4.0, "neededDecelMps2AtLeast": 1.0}},
    "VC-DRIVING-038": {"worldSideControlCalls": 0, "controlSource": "actuationAdapter",
                       "match": "seq and crc of S out.driving_command = seq and checkValue of A in.driving_command"},
    "VC-DRIVING-040": {"imminent": {"ttcSAtMost": 4.0, "neededDecelMps2AtLeast": 1.0, "inLane": True}},
    "VC-DRIVING-041": {"imminent": {"ttcSAtMost": 4.0, "neededDecelMps2AtLeast": 1.0, "inLane": True},
                       "emergencyBrakingMps2": 5.0},
    "VC-DRIVING-043": {"match": "receipt requested and issue_time_sim_ms = S out.warning_request bytes"},
    "VC-DRIVING-044": {"recordBeforeFirstCommand": True, "diffBytesAbove": 0},
}

CASES = {
    "VC-DRIVING-036": lambda sess, desk: judged_settings_campaign("VC-DRIVING-036", sess, run_036,
                                                                 THRESHOLDS["VC-DRIVING-036"]),
    "VC-DRIVING-037": lambda sess, desk: judged_settings_campaign("VC-DRIVING-037", sess, run_037,
                                                                 THRESHOLDS["VC-DRIVING-037"]),
    "VC-DRIVING-042": lambda sess, desk: judged_settings_campaign("VC-DRIVING-042", sess, run_042,
                                                                 THRESHOLDS["VC-DRIVING-042"]),
    "VC-DRIVING-038": lambda sess, desk: every_run_campaign("VC-DRIVING-038", sess, run_038, terms.ALL_SETTINGS,
                                                           THRESHOLDS["VC-DRIVING-038"], stop_clause=stop_038),
    "VC-DRIVING-040": lambda sess, desk: every_run_campaign("VC-DRIVING-040", sess, run_040, terms.ALL_SETTINGS,
                                                           THRESHOLDS["VC-DRIVING-040"]),
    "VC-DRIVING-041": lambda sess, desk: every_run_campaign("VC-DRIVING-041", sess, run_041, terms.ALL_SETTINGS,
                                                           THRESHOLDS["VC-DRIVING-041"]),
    "VC-DRIVING-043": lambda sess, desk: every_run_campaign("VC-DRIVING-043", sess, run_043, terms.JUDGED_SETTINGS,
                                                           THRESHOLDS["VC-DRIVING-043"], stop_clause=stop_043),
    "VC-DRIVING-044": lambda sess, desk: every_run_campaign("VC-DRIVING-044", sess, run_044, terms.ALL_SETTINGS,
                                                           THRESHOLDS["VC-DRIVING-044"],
                                                           extra=lambda s, runs: desk_044(s, runs, desk)),
}


def evaluate(session: Session, desk: dict | None = None) -> dict:
    """Every case on one session: {vc: result}."""
    return {vc: fn(session, desk) for vc, fn in CASES.items()}
