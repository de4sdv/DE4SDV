"""Judge one S1 session: every case of INC-DRIVING-002 that reads runs, with the criteria record and the evaluator
revision that each verdict names (RetainedAssistanceRunEvidence criteriaRecordIdentity and evaluatorRevision,
driver_assistance_verification_evidence.sysml:195-198, :237-238).

    python3 evaluate_da_campaign.py --session <incoming session root> --out verdicts.json [--desk-044 file]

The desk record of VC-DRIVING-044 (plan lane F2) is read from --desk-044, else from reproduction_044.json at the
session root. `--write-criteria` regenerates da_criteria_record.json from the model and cases_da.THRESHOLDS.
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
    **{vc: "EVALUATOR READING: from 2.0 s before the functional part to its end"
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
    "EVALUATOR READING: a fail on any run read gives fail, before error, blocked and inconclusive",
    "036 and 037 are conditional on ASM-DRIVING-005, the calibration of the simulated deceleration "
    "(driver_assistance_verification_evidence.sysml:299-300; plan D-S1-2)",
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


def run(root: Path, desk_path: Path | None) -> dict:
    root = Path(root)
    sess = runio_da.discover(root)
    desk = None
    path = desk_path or (root / "reproduction_044.json")
    if path.is_file():
        desk = {"VC-DRIVING-044": json.loads(path.read_text())}
    crit = criteria_record_identity()
    rev, blobs = evaluator_revision()
    cases = cases_da.evaluate(sess, desk)
    calib = calibration_decel(root)
    for vc in ("VC-DRIVING-036", "VC-DRIVING-037"):
        cases[vc]["measured"]["calibrationDecel"] = calib
        cases[vc]["notes"].append("conditional on ASM-DRIVING-005: the calibration of the simulated deceleration "
                                  "comes before the first judged run (driver_assistance_verification_evidence"
                                  ".sysml:299-300); calibrationDecel holds the session's calib-decel summary")
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
            "problems": sess.problems, "cases": cases}


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
    for vc, res in doc["cases"].items():
        print(f"{vc} {res['outcome']} {res['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
