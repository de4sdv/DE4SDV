"""Replay the evaluators over a run directory and print the outcomes as JSON.

    python -m de4sdv_broker_path_bench.run <run-dir> [--case VC-MW-015 ...]
    python -m de4sdv_broker_path_bench.run --vc020-runs <hmi-down> <ivi-vm-down> <core-down> <pair-restart>

It reads only the raw artifacts of the directories. It prints one JSON object
with a result per case; it writes no verdict into any record and makes no
claim beyond the bounded outcome of each evaluator. The exit code is 0 only
when every requested case gives a pass.

VC-MW-020 runs one condition per run directory, and its verification case makes a pass cover
the four conditions. So the reported VC-MW-020 outcome is the case outcome
over the conditions given: a fail or an error of one condition is the case's;
a pass needs all four conditions present and passing; anything else is
missing evidence. Each condition's own result is kept under ``conditions``.

The report also holds the sha256 of every artifact it read and a digest of
the evaluator sources, so a result can be tied to its inputs and its code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .evaluators import EVALUATORS, evaluate_unsubscribed_discard, load_run
from .outcome import ERROR, FAIL, INCONCLUSIVE, PASS, verdict

#: The four conditions of VC-MW-020 (middleware_score_verification_evidence.sysml).
VC020_CONDITIONS = ("hmi_down", "ivi_vm_down", "sdv_core_vm_down", "pair_restart")


def _artifact_digests(run_dir: Path) -> dict[str, str]:
    digests = {}
    if run_dir.is_dir():
        for path in sorted(run_dir.iterdir()):
            if path.is_file() and not path.is_symlink():
                digests[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def _evaluator_digest() -> str:
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).resolve().parent.glob("*.py")):
        digest.update(path.name.encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def vc020_case(condition_results: list[dict]) -> dict:
    """The VC-MW-020 case outcome over its condition runs (a pass covers the four conditions)."""
    conditions: dict[str, dict] = {}
    for result in condition_results:
        name = result.get("measurements", {}).get("condition", "unnamed")
        # A second run of one condition keeps the worse outcome.
        previous = conditions.get(name)
        if previous is None or previous["outcome"] == PASS:
            conditions[name] = result
    outcomes = [result["outcome"] for result in condition_results]
    missing = [name for name in VC020_CONDITIONS if name not in conditions]
    if ERROR in outcomes:
        case = ERROR
    elif FAIL in outcomes:
        case = FAIL
    elif not missing and all(result["outcome"] == PASS for result in condition_results):
        case = PASS
    else:
        case = INCONCLUSIVE
    note = ("a pass covers these four conditions only; it does not show the stored frames of every other late or "
            "repeated subscription in the host half (GAP-MW-039)")
    return {"case": "VC-MW-020", "scope": "case over its conditions", "outcome": case, "verdict": verdict(case),
            "conditions": conditions, "missing_conditions": missing, "claim_boundary": note}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", nargs="?", help="the run directory with the raw artifacts")
    parser.add_argument("--case", action="append", choices=sorted(EVALUATORS),
                        help="a case to evaluate (default: every case the directory supports)")
    parser.add_argument("--vc020-runs", nargs="+", metavar="RUN_DIR",
                        help="the VC-MW-020 condition runs (one per condition) to give the case outcome over")
    parser.add_argument("--out", help="write the JSON report to this file as well as stdout")
    arguments = parser.parse_args(argv)
    if not arguments.run_dir and not arguments.vc020_runs:
        parser.error("give a run directory, or --vc020-runs with the condition runs")

    results: dict[str, dict] = {}
    artifacts: dict[str, dict[str, str]] = {}
    if arguments.run_dir:
        run = load_run(arguments.run_dir)
        artifacts[str(Path(arguments.run_dir))] = _artifact_digests(Path(arguments.run_dir))
        for case in arguments.case or sorted(EVALUATORS):
            result = EVALUATORS[case](run).as_dict()
            results[case] = vc020_case([result]) if case == "VC-MW-020" else result
    if arguments.vc020_runs:
        condition_results = []
        for run_dir in arguments.vc020_runs:
            condition_results.append(evaluate_unsubscribed_discard(load_run(run_dir)).as_dict())
            artifacts[str(Path(run_dir))] = _artifact_digests(Path(run_dir))
        results["VC-MW-020"] = vc020_case(condition_results)

    report = {"run_dir": arguments.run_dir, "results": results, "artifact_sha256": artifacts,
              "evaluator_sha256": _evaluator_digest()}
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if arguments.out:
        Path(arguments.out).write_text(text + "\n")
    return 0 if results and all(result["outcome"] == PASS for result in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
