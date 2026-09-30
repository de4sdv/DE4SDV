#!/usr/bin/env python3
"""Exercise the four existing Core snapshot modes and retain honest receipts.

This is read-only to Git/API/GitHub. It neither ingests nor accepts the pilot.
Historical replay requires --allow-historical; current evidence requires exact
artifact/HEAD equality. Reported API timings are retained-export replay timings,
not live network-load measurements. Exit 0 means battery evidence produced;
Core/product acceptance is always explicitly not established by this command.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic import operational_exit as oe  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--validation-run", required=True)
    parser.add_argument("--expected-revision")
    parser.add_argument("--allow-historical", action="store_true")
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--independent-review", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        parser.error("output directory already exists; choose a fresh path")
    out.mkdir(parents=True)
    try:
        if not args.validation_run.isdecimal():
            raise oe.OperationalExitRefusal(["validation-run must be an exact numeric run id"])
        artifacts = oe.validate_ingestion_artifacts(args.artifacts)
        repo = args.repo.resolve()
        head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        executor_head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
        scope = oe.classify_scope(artifact_git_commit=artifacts.git_commit, repo_head=head,
                                  expected_revision=args.expected_revision)
        if scope.mode == "current-exact-revision" and executor_head != head:
            scope = oe.classify_scope(artifact_git_commit=artifacts.git_commit, repo_head=executor_head,
                                      expected_revision=args.expected_revision)
        if scope.mode == "refused-expectation-mismatch":
            raise oe.OperationalExitRefusal(list(scope.reasons))
        if scope.historical and not args.allow_historical:
            raise oe.OperationalExitRefusal([*scope.reasons, "historical diagnostic replay requires --allow-historical"])
        battery = oe.run_battery(script=ROOT / "scripts/run_snapshot_parity.py", repo=repo,
                                 artifacts=artifacts, out_dir=out / "battery", spec=args.spec,
                                 validation_run=args.validation_run,
                                 artifact_label="full-model-api-ingestion-" + artifacts.git_commit)
        expectations_path = out / "battery/build/expectations.json"
        expectations = json.loads(expectations_path.read_text()) if expectations_path.exists() else {}
        review = oe.bind_independent_review(record_path=args.independent_review,
                                            evaluation_key=battery.verdict.get("evaluation_key") or "",
                                            git_commit=artifacts.git_commit,
                                            contract_digest=expectations.get("contract_digest", ""))
        dirty = bool(subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True).strip())
        environment = {"system": platform.system(), "machine": platform.machine(),
                       "python": platform.python_version(), "executor_git_head": executor_head,
                       "model_repo_git_head": head,
                       "executor_source_dirty": dirty, "runner_role": "not-established-by-local-CLI"}
        receipt = oe.build_receipt(artifacts=artifacts, battery_executions=battery.executions,
                                   verdict=battery.verdict, scope=scope, independent_review=review,
                                   validation_run=args.validation_run,
                                   artifact_label="full-model-api-ingestion-" + artifacts.git_commit,
                                   environment=environment)
        code = 0 if receipt["method_decision"]["status"] == "evidence-produced" else 2
    except (oe.OperationalExitRefusal, OSError, subprocess.CalledProcessError, ValueError) as error:
        receipt = {"schema": oe.RECEIPT_SCHEMA, "status": "refused-input",
                   "refusals": list(getattr(error, "reasons", ())) or [str(error)],
                   "core_accepted": False, "product_accepted": False}
        code = 2
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"receipt": str(out / "receipt.json"), "exit_code": code,
                      "scope": receipt.get("scope"), "method_decision": receipt.get("method_decision"),
                      "refusals": receipt.get("refusals")}, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
