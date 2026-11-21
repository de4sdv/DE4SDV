"""Judge one S1 session: every case of INC-DRIVING-002 that reads runs, with the criteria record and the evaluator
revision that each verdict names (RetainedAssistanceRunEvidence criteriaRecordIdentity and evaluatorRevision,
driver_assistance_verification_evidence.sysml:195-198, :237-238).

    python3 evaluate_da_campaign.py --session <incoming session root> --out verdicts.json [--desk-044 file]

The desk record of VC-DRIVING-044 (plan lane F2) is read from --desk-044, else from reproduction_044.json at the
session root. `--write-criteria` regenerates da_criteria_record.json from the model and cases_da.THRESHOLDS.

A session whose session.json says `rehearsal` true is never judged (lead contract 4 of 2026-11-20): the output names
the reason and holds no case, and the exit status is 3. Each run's evidence record (RetainedAssistanceRunEvidence,
evidence_record.py) goes into the output; a run whose record is partial gives inconclusiveMissingEvidence for that
run, never pass and never fail (driver_assistance_verification_evidence.sysml:126-127, :211-212; the lead's reading
of 2026-11-21), so a case's fail stands only when a run that shows it has a complete record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import cases_da  # noqa: E402
import evidence_record  # noqa: E402
import runio_da  # noqa: E402

CRITERIA_FILE = HERE / "da_criteria_record.json"
CRITERIA_SCHEMA = "de4sdv.driving.da-criteria-record.v1"
# evaluatorRevision: the blobs of this folder's own .py and .json files (rule 30: not a commit, not the folder's
# subtree hash, which a changed document would move).
EVALUATOR_FILES = tuple(sorted(p.name for p in HERE.iterdir() if p.is_file() and p.suffix in (".py", ".json")))
OUTPUT_SCHEMA = "de4sdv.driving.da-campaign-verdicts.v1"

RUNS_READ = {
    "VC-DRIVING-036": "the two runs of each judged setting (SC-DRIVING-012@20/@42/@60, SC-DRIVING-013@30/@60)",
    "VC-DRIVING-037": "the two runs of each judged setting (SC-DRIVING-012@20/@42/@60, SC-DRIVING-013@30/@60)",
    "VC-DRIVING-042": "the two runs of each judged setting (SC-DRIVING-012@20/@42/@60, SC-DRIVING-013@30/@60)",
    "VC-DRIVING-038": "the fourteen runs of the seven settings, and the stop run for the stop clause",
    "VC-DRIVING-040": "the fourteen runs of the seven settings",
    "VC-DRIVING-041": "the fourteen runs of the seven settings",
    "VC-DRIVING-043": "the ten runs of SC-DRIVING-012 and -013, and the stop run for the stop clause",
    "VC-DRIVING-044": "the fourteen runs of the seven settings, and the desk reproduction (plan lane F2)",
}
JUDGED_WINDOW = {
    **{vc: "the case's own window, lead decision of 2026-11-20: from 2.0 s before the functional part to its end "
           "(driver_assistance_verification_evidence.sysml:23-27, :203-207 fix the whole run only for a criterion "
           "over every run)"
       for vc in ("VC-DRIVING-036", "VC-DRIVING-037", "VC-DRIVING-042")},
    **{vc: "the whole run, first to last world tick (driver_assistance_verification_evidence.sysml:206-207)"
       for vc in ("VC-DRIVING-038", "VC-DRIVING-040", "VC-DRIVING-041", "VC-DRIVING-043", "VC-DRIVING-044")},
}
READINGS = [
    "BENCH READING: travels straight = heading within 2.0 deg of the target's (B/world-side/scenarios.py:29-31)",
    "BENCH READING: a stationary target's speed reached at closing <= 0.05 m/s (B/world-side/scenarios.py:33-34)",
    "EVALUATOR READING: a moving target's speed reached at closing <= 0 (plan A2)",
    "EVALUATOR READING: the relative impact speed is the closing on the tick before the first targetContact",
    "EVALUATOR READING: the last driving command at a tick is the newest with issueTime_sim_s <= simTimeS",
    "EVALUATOR READING: 042 counts the warning starts up to the end of the functional part",
    "EVALUATOR READING: 038's stop clause: a driving command reaches the actuation after the stop as an "
    "out.ackermann_control of the actuation adapter after stopInstantMonoNs or a rise of worldSideControlCalls; the "
    "changes of the world's control (hero.get_control(), the simulator's Ackermann controller output) are a note",
    "EVALUATOR READING: a fail on any run read gives fail, before error, blocked and inconclusive",
    "036 and 037 are conditional on ASM-DRIVING-005, the calibration of the simulated deceleration "
    "(driver_assistance_verification_evidence.sysml:299-300; plan D-S1-2); they report the requested and the read-back "
    "Ackermann gains, 'unrecorded' when the session holds none",
    "042: a warning start at least 1.0 s of simulation time before the first emergency braking start, when the run "
    "has one; a warning still on at the braking is not asked",
    "040 and 041 read the guidance of SC-DRIVING-014 and -015 from setting_record.json site.guidance "
    "(SiteSpec.as_record()); each speed and time to collision of the guidance must hold a value",
    "a run whose evidence record (RetainedAssistanceRunEvidence) is partial gives inconclusive for that run, never pass "
    "and never fail (driver_assistance_verification_evidence.sysml:126-127, :211-212; the lead's reading of "
    "2026-11-21): a case's fail stands only when a run that shows it has a complete record, a pass with any partial "
    "record read becomes inconclusive, and a note names the outcome observed before the rule",
    "a rehearsal session (session.json rehearsal true) is not judged",
]


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def evaluator_revision(root: Path | None = None) -> tuple[str, dict]:
    root = Path(root) if root is not None else HERE
    names = sorted(p.name for p in root.iterdir() if p.is_file() and p.suffix in (".py", ".json"))
    blobs = {name: git_blob((root / name).read_bytes()) for name in names}
    digest = hashlib.sha256("".join(f"{blobs[n]} {n}\n" for n in sorted(blobs)).encode()).hexdigest()
    return f"blobs:{digest}", blobs


def criteria_record_identity() -> str:
    return "sha256:" + hashlib.sha256(CRITERIA_FILE.read_bytes()).hexdigest()


def build_criteria_record(repo: Path) -> dict:
    nr = repo / cases_da.NR
    lines = nr.read_text().splitlines()
    cases = {}
    for vc, (req, clause) in cases_da.REQUIREMENT.items():
        line = int(clause.rsplit(":", 1)[1])
        m = re.search(r'attribute :>> successCriteria = "(.*)";', lines[line - 1])
        if not m or req not in "\n".join(lines[max(0, line - 8):line]):
            raise SystemExit(f"{clause}: no successCriteria of {req} on that line")
        cases[vc] = {"requirement": req, "successClause": clause, "successCriteria": m.group(1),
                     "runsRead": RUNS_READ[vc], "judgedWindow": JUDGED_WINDOW[vc],
                     "thresholds": cases_da.THRESHOLDS[vc]}
    return {"schema": CRITERIA_SCHEMA, "increment": "INC-DRIVING-002", "outcomes": list(cases_da.OUTCOMES),
            "droppedImageRule": cases_da.DROP_RULE, "readings": READINGS, "cases": cases}


def calibration_decel(root: Path) -> dict | None:
    """The session's calib-decel summary (calibrate/calib_decel/simulator/calibration_decel.json), or None."""
    for p in sorted(Path(root).rglob("calibration_decel.json")):
        try:
            rec = json.loads(p.read_text())
        except json.JSONDecodeError:
            return {"file": str(p.relative_to(root)), "error": "not JSON"}
        s = rec.get("summary") if isinstance(rec, dict) else None
        s = s if isinstance(s, dict) else {}
        return {"file": str(p.relative_to(root)), "allFollowWithinProposal": s.get("allFollowWithinProposal"),
                "worstRatio": s.get("worstRatio")}
    return None


GAIN_KEY = re.compile(r"ackermann.*gain|gain.*ackermann", re.I)


def _gain_fields(obj, path: str = "") -> list:
    """Every (dotted key, value) whose key names Ackermann gains, at any depth (the field names are not fixed yet:
    lead contract 5 of 2026-11-20)."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{path}.{k}" if path else str(k)
            if GAIN_KEY.search(str(k)):
                out.append((key, v))
            else:
                out += _gain_fields(v, key)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += _gain_fields(v, f"{path}[{i}]")
    return out


def ackermann_gains(root: Path, session: dict) -> dict:
    """The requested gains (session.json) and the gains read back on the simulator host (each run's
    setting_record.json, the calibration records), as found; "unrecorded" when none is found (lead contract 5)."""
    requested = [{"file": "session.json", "key": k, "value": v} for k, v in _gain_fields(session)]
    read_back = []
    files = sorted(set(Path(root).rglob("setting_record.json")) | set(Path(root).rglob("calibration_*.json")))
    for p in files:
        try:
            rec = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        read_back += [{"file": str(p.relative_to(root)), "key": k, "value": v} for k, v in _gain_fields(rec)]
    return {"requested": requested or "unrecorded", "readBack": read_back or "unrecorded"}


def _gains_text(found) -> str:
    if found == "unrecorded":
        return "unrecorded"
    return "; ".join(f"{g['file']} {g['key']} = {json.dumps(g['value'])}" for g in found)


def condition_note(calib: dict | None, gains: dict) -> str:
    """The condition of every verdict of 036 and 037 while ASM-DRIVING-005 is unproven, with what the session holds
    about it: the calib-decel summary and the Ackermann gains (lead contract 5), on pass and on fail alike."""
    if calib is None:
        summary = "calib-decel summary unrecorded (no calibration_decel.json in the session)"
    elif "error" in calib:
        summary = f"calib-decel summary unreadable ({calib['file']}: {calib['error']})"
    else:
        summary = (f"calib-decel summary ({calib['file']}): worstRatio {json.dumps(calib.get('worstRatio'))}, "
                   f"allFollowWithinProposal {json.dumps(calib.get('allFollowWithinProposal'))}")
    return ("conditional on ASM-DRIVING-005: the calibration of the simulated deceleration comes before the first "
            "judged run (driver_assistance_verification_evidence.sysml:299-300); " + summary
            + f"; Ackermann gains: requested {_gains_text(gains['requested'])}, read back "
            + f"{_gains_text(gains['readBack'])}")


def refusal(session: dict) -> str | None:
    """Why a session is not judged, or None: a rehearsal (lead contract 4 of 2026-11-20)."""
    value = session.get("rehearsal") if isinstance(session, dict) else None
    if value is None or value is False:
        return None
    return (f"session.json rehearsal is {json.dumps(value)}: a rehearsal session is never judged (lead contract 4 "
            "of 2026-11-20)")


def partial_record_rule(res: dict, records: dict) -> None:
    """The rule of :126-127 and :211-212 on one case, as the lead read it on 2026-11-21: a run whose evidence record is
    partial gives inconclusive for that run, never pass and never fail. The case's outcome is combined again from the
    runs' outcomes so read, the stop clause's and the outcomes of the clauses that no run shows (044's desk
    reproduction, which no run record touches): a fail stands only when a run that shows it has a complete record, and
    a pass with any partial record read becomes inconclusive. A note names the outcome observed before the rule."""
    entries = list(res["measured"].get("runs", []))
    sc = res["measured"].get("stopClause")
    if isinstance(sc, dict) and sc.get("run"):
        entries.append(sc)
    partial = []
    for e in entries:
        r = e["run"]
        if r in records and records[r]["outcome"] != evidence_record.COMPLETE and r not in partial:
            partial.append(r)
    for r in partial:
        res["missing"].append(f"the evidence record of run {r} (RetainedAssistanceRunEvidence) is partial, "
                              f"empty: {', '.join(records[r]['emptyAttributes'])} (driver_assistance_verification"
                              "_evidence.sysml:211-212: a missing or partial record gives inconclusive, never "
                              "pass)")
    if not partial or res["outcome"] not in (cases_da.PASS, cases_da.FAIL):
        return
    read = [cases_da.INCONCLUSIVE if e["run"] in partial and e["outcome"] in (cases_da.PASS, cases_da.FAIL)
            else e["outcome"] for e in entries]
    observed = res["outcome"]
    outcome = cases_da.combine(read + list(res["measured"].get("outcomesWithoutRun", [])), res["missing"])
    if outcome == observed:
        return
    shown = [e["run"] for e in entries if e["outcome"] == observed and e["run"] in partial]
    res["outcome"], res["verdict"] = outcome, cases_da.verdict(outcome)
    res["notes"].append(f"observed {observed} before the rule on partial evidence records; {outcome} because "
                        f"the evidence record of each run read that shows it is partial ({', '.join(shown)}): a "
                        "missing or partial record gives inconclusive, never pass (driver_assistance_verification_"
                        "evidence.sysml:126-127, :211-212; the lead's reading of 2026-11-21: never fail either)")


def run(root: Path, desk_path: Path | None) -> dict:
    root = Path(root)
    sj = root / "session.json"
    why = refusal(runio_da.read_json(sj)) if sj.is_file() else None
    if why is not None:
        return {"schema": OUTPUT_SCHEMA, "session": str(root),
                "sessionId": runio_da.read_json(sj).get("session_id"), "refused": why, "cases": {}}
    sess = runio_da.discover(root)
    desk = None
    path = desk_path or (root / "reproduction_044.json")
    if path.is_file():
        desk = {"VC-DRIVING-044": json.loads(path.read_text())}
    crit = criteria_record_identity()
    rev, blobs = evaluator_revision()
    cases = cases_da.evaluate(sess, desk)
    calib = calibration_decel(root)
    gains = ackermann_gains(root, sess.session)
    for vc in ("VC-DRIVING-036", "VC-DRIVING-037"):
        cases[vc]["measured"]["calibrationDecel"] = calib
        cases[vc]["measured"]["ackermannGains"] = gains
        cases[vc]["notes"].append(condition_note(calib, gains))
    # the evidence record of each run (lane D), and the rule of :211-212 on every case that reads a run
    outcomes: dict = {}
    for vc, res in cases.items():
        for e in res["measured"].get("runs", []):
            outcomes.setdefault(e["run"], {})[vc] = e["outcome"]
        sc = res["measured"].get("stopClause")
        if isinstance(sc, dict) and sc.get("run"):
            outcomes.setdefault(sc["run"], {})[f"{vc} stop clause"] = sc["outcome"]
    records = evidence_record.build_all(sess, criteria=crit, revision=rev,
                                        desk=(desk or {}).get("VC-DRIVING-044"), outcomes=outcomes)
    for res in cases.values():
        partial_record_rule(res, records)
    for res in cases.values():
        res["criteriaRecordIdentity"] = crit
        res["evaluatorRevision"] = rev
    runs = [{"run": r.run_id, "setting": r.setting_id, "repetition": r.repetition, "kind": r.kind,
             "runIdentity": r.session_entry.get("runIdentity")} for r in sess.runs]
    if sess.stop_run is not None:
        r = sess.stop_run
        runs.append({"run": r.run_id, "setting": r.setting_id, "repetition": None, "kind": "stop",
                     "runIdentity": r.session_entry.get("runIdentity")})
    return {"schema": OUTPUT_SCHEMA, "session": str(root), "sessionId": sess.session.get("session_id"),
            "criteriaRecordIdentity": crit, "evaluatorRevision": rev, "evaluatorBlobs": blobs, "runs": runs,
            "problems": sess.problems, "cases": cases, "evidenceRecords": records}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--session", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--desk-044", type=Path, default=None)
    ap.add_argument("--write-criteria", action="store_true")
    a = ap.parse_args(argv)
    if a.write_criteria:
        rec = build_criteria_record(HERE.parents[2])
        CRITERIA_FILE.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
        print(CRITERIA_FILE)
        return 0
    if a.session is None or a.out is None:
        ap.error("--session and --out are needed")
    doc = run(a.session, a.desk_044)
    a.out.write_text(json.dumps(doc, indent=1) + "\n")
    if doc.get("refused"):
        print(f"refused: {doc['refused']}")
        return 3
    for vc, res in doc["cases"].items():
        print(f"{vc} {res['outcome']} {res['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
