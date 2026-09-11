#!/usr/bin/env python3
"""Advisory delivery-gate observation for one PR (Lane D).

Runs ``pr_gate_status`` in advisory/shadow mode against LIVE PR state:
repository/PR identity, exact observed head/base (read, evidence collection,
re-read), CI check results, review records, changed-file inventory, and the
live branch-protection policy — all read via ``gh`` CLI read-only commands.

This script observes. It never merges, approves, comments, dispatches,
or changes any repository or security setting; GitHub platform merge
protection remains authoritative for the actual merge.

Exit codes: 0 report produced (readiness may honestly be BLOCKED); 2 refused
(could not establish the policy/baseline observation); 1 unexpected error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic import delivery_gate as dg  # noqa: E402

_SUMMARY_FIELDS = (
    "evaluation_key",
    "method_id",
    "contract_id",
    "contract_digest",
    "policy_bundle_id",
    "git_commit",
    "sysml_project_id",
    "sysml_commit_id",
    "scope",
    "assessment_coverage",
    "evaluation_state",
    "conformance_verdict",
    "required_units",
    "failed_ids",
    "indeterminate_ids",
    "errored_ids",
    "unassessed_ids",
)


def _load_summary(path: Path) -> dg.ConformanceSummary:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"refused: {path} is not a JSON object")
    fields = {field: value.get(field) for field in _SUMMARY_FIELDS}
    missing = [
        field
        for field, observed in fields.items()
        if observed is None and field not in {"evaluation_state", "conformance_verdict"}
    ]
    if missing:
        raise SystemExit(f"refused: conformance summary is missing fields {missing}")
    for name in ("required_units", "failed_ids", "indeterminate_ids", "errored_ids", "unassessed_ids"):
        fields[name] = tuple(str(item) for item in (fields[name] or ()))
    return dg.ConformanceSummary(**fields)  # type: ignore[arg-type]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument(
        "--summary",
        type=Path,
        default=None,
        help=(
            "Conformance summary JSON for the exact PR-head revision; omit to "
            "observe a PR whose head has no evaluated conformance result"
        ),
    )
    parser.add_argument(
        "--policy-bearing-path",
        action="append",
        default=[],
        help="Path prefix whose change requires a method-change authorization",
    )
    parser.add_argument(
        "--extra-required-obligation",
        action="append",
        default=[],
        help="An additional required delivery obligation (unsupported in this V1 slice)",
    )
    parser.add_argument(
        "--cross-check",
        choices=("agreed", "disagreed", "timeout", "partial", "not-run"),
        default=None,
    )
    parser.add_argument("--cross-check-detail", default="")
    parser.add_argument("--evaluator-disposition", default="")
    parser.add_argument("--independent-disposition", default="")
    parser.add_argument("--independent-source", default="")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    source = dg.GhCliDeliverySource(repository=args.repository, pr_number=args.pr)

    # Read the live policy first so the observation is judged against an
    # explicitly captured revision; the gate re-reads it during the run so a
    # mid-run policy change is detected as POLICY_REVISION_MISMATCH.
    try:
        policy_observation = source.read_policy_observation()
    except dg.DeliveryEvidenceError as error:
        print(json.dumps({"status": "refused-policy-unavailable", "reason": str(error)}, indent=2))
        return 2

    policy = dg.DeliveryPolicy(
        policy_id="de4sdv.delivery.advisory.v1",
        revision=str(policy_observation["revision"]),
        required_checks=tuple(policy_observation["required_checks"]),
        required_approvals=int(policy_observation["required_approvals"]),
        require_cross_check=True,
        policy_bearing_paths=tuple(args.policy_bearing_path),
        extra_required_obligations=tuple(args.extra_required_obligation),
    )
    cross_check = None
    if args.cross_check is not None:
        cross_check = dg.CrossCheckRecord(
            parity=args.cross_check,
            parity_detail=args.cross_check_detail,
            evaluator_disposition=args.evaluator_disposition,
            independent_disposition=args.independent_disposition,
        )

    conformance = _load_summary(args.summary) if args.summary is not None else None
    payload = dg.pr_gate_status(
        repository=args.repository,
        pr_number=args.pr,
        policy=policy,
        source=source,
        conformance=conformance,
        cross_check=cross_check,
    )
    payload["tool_policy_source"] = {
        "branch_protection": policy_observation.get("source"),
        "required_checks": policy_observation.get("required_checks"),
        "required_approvals": policy_observation.get("required_approvals"),
    }
    payload["independent_source"] = args.independent_source

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "readiness": payload["readiness"],
                "blocking_reasons": payload["blocking_reasons"],
                "observed_head": payload["observation"]["head_sha"],
                "observed_base": payload["observation"]["base_sha"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
