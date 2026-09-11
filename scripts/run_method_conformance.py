#!/usr/bin/env python3
"""Run the deterministic method-conformance evaluation for the real pilot.

Consumes the retained exact-head candidate artifact produced by the Lane B
privileged run (committed-candidate path) and the candidate revision's
committed evidence/registry state, then emits the canonical disposition for
INC-AEBS-009D. Read-only: no writes to the repository, no API service, no
privileged ingestion (the evaluation changes no model/serialization
semantics; it consumes the already-proven API boundary).

Usage:
    python scripts/run_method_conformance.py \
        --repo <checkout> \
        --candidate-export /path/de4sdv-candidate-export.json \
        --candidate-binding /path/de4sdv-candidate-binding.json \
        --output /path/disposition.json

Exit codes: 0 evaluation produced; 2 refused (policy-closure mismatch or
unsupported input), never a fabricated green result.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.method_evaluator import (  # noqa: E402
    ApprovedMethodSelection,
    MethodConformanceService,
    ReadinessTarget,
    RevisionIdentity,
)
from de4sdv.semantic.method_pilot import (  # noqa: E402
    BENCH_ROOT,
    PILOT_PROFILES,
    PILOT_SCOPE_RECORD,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--candidate-export", type=Path, required=True)
    parser.add_argument("--candidate-binding", type=Path, required=True)
    parser.add_argument(
        "--candidate-revision",
        default=None,
        help="Git revision of the evaluated candidate (default: binding git_commit)",
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=None,
        help="Approved contract twin (default: docs/method-conformance/pilot-obligations.yaml)",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    return run(
        repo=args.repo.resolve(),
        candidate_export=args.candidate_export,
        candidate_binding=args.candidate_binding,
        candidate_revision=args.candidate_revision,
        spec=args.spec,
        output=args.output,
    )


def run(
    *,
    repo: Path,
    candidate_export: Path,
    candidate_binding: Path,
    candidate_revision: str | None,
    spec: Path | None,
    output: Path | None,
) -> int:
    from de4sdv.semantic import method_pilot as mp

    binding = json.loads(candidate_binding.read_text())
    revision = candidate_revision or str(binding["git_commit"])

    approved = mp.load_approved_contract_from_yaml(
        spec or repo / "docs/method-conformance/pilot-obligations.yaml"
    )

    export = json.loads(candidate_export.read_text())
    elements = export.get("elements") or []
    export_revision = str(export.get("git_commit") or "")
    report: dict[str, object] = {
        "schema": "de4sdv-method-conformance-run/v1",
        "candidate_revision": revision,
        "candidate_export_revision": export_revision,
        "candidate_binding_revision": str(binding.get("git_commit") or ""),
        "element_count": len(elements),
    }
    # The artifact revision must be the same committed content as the
    # evaluated revision. When they differ (squash-merge heads), prove the
    # relevant subtrees are identical.
    if export_revision and export_revision != revision:
        probe = subprocess.run(
            [
                "git", "-C", str(repo), "diff", "--stat", export_revision, revision,
                "--", "textual-notation-of-model", BENCH_ROOT,
            ],
            capture_output=True,
            text=True,
        )
        if probe.returncode != 0:
            report["artifact_revision_relation"] = (
                f"cannot compare {export_revision}..{revision}: {probe.stderr.strip()}"
            )
        else:
            diff_lines = [l for l in probe.stdout.splitlines() if l.strip()]
            report["artifact_revision_relation"] = (
                "subtree-identical" if not diff_lines else f"SUBTREE-DIFFERS: {diff_lines}"
            )

    candidate_source = mp.GitRevisionFileSource(repo, revision)
    declared_head_probe = mp.decode_declared_tested_scope(elements)
    scope_item, _, scope_diagnostics = declared_head_probe
    declared_head = None
    if scope_item is not None:
        by_id = mp._elements_by_id(elements)
        _, declared_head = mp._member_text_value(by_id, scope_item, "executionHead")
    tested_source = (
        mp.GitRevisionFileSource(repo, declared_head) if declared_head else None
    )

    # Reproduction evidence: the record's execution-identity values must
    # reproduce at the declared tested head under the pinned reconstruction
    # rule (script-level evidence, not a test substitute).
    reproduction: dict[str, str] = {}
    if tested_source is not None:
        input_paths, input_diagnostics = mp._claimed_input_paths(tested_source)
        input_map: dict[str, str] = {}
        for relative in input_paths:
            blob = tested_source.read_bytes(relative)
            if blob is None:
                continue
            input_map[relative.replace(f"{BENCH_ROOT}/", "")] = __import__(
                "hashlib"
            ).sha256(blob).hexdigest()
        manifest, _ = mp.load_campaign_manifest(candidate_source)
        records, _ = mp.load_records(candidate_source, manifest)
        for profile in PILOT_PROFILES:
            record = records.get(profile) or {}
            provenance = record.get("provenance") or {}
            observed = mp.reconstruct_manifest_sha256(input_map, profile)
            expected = str(provenance.get("override_execution_manifest_sha256") or "")
            reproduction[profile] = (
                "reproduced" if observed == expected else f"MISMATCH ({observed} != {expected})"
            )
        top_observed = mp.reconstruct_manifest_sha256(input_map, None)
        top_expected = str(
            (records.get(PILOT_PROFILES[0]) or {}).get("provenance", {}).get(
                "execution_manifest_sha256"
            )
            or ""
        )
        reproduction["execution_manifest_sha256"] = (
            "reproduced" if top_observed == top_expected else "MISMATCH"
        )
        if input_diagnostics:
            reproduction["input_diagnostics"] = "; ".join(input_diagnostics)
    report["tested_head_reproduction"] = reproduction

    assembly = mp.assemble_pilot_context(
        approved_contract=approved,
        elements=elements,
        revision=RevisionIdentity(
            git_commit=revision,
            sysml_project_id=str(binding.get("sysml_project_id") or ""),
            sysml_commit_id=str(binding.get("sysml_commit_id") or ""),
            scope=str(binding.get("scope") or ""),
        ),
        candidate_source=candidate_source,
        tested_source=tested_source,
    )
    report["assembly_diagnostics"] = list(assembly.diagnostics)
    if assembly.closure_mismatches:
        report["status"] = "refused-policy-closure-mismatch"
        report["closure_mismatches"] = list(assembly.closure_mismatches)
        report["diagnostics"] = mp.refusal_diagnostics(assembly.closure_mismatches)
        _emit(report, output)
        print(json.dumps(report, indent=2))
        return 2

    # Route the four C-owned surfaces through the same service so the report
    # proves one canonical evaluation identity (evaluation_count == 1).
    selection = ApprovedMethodSelection(
        method_id=approved.method_id,
        contract_id=approved.contract_id,
        policy_bundle_id=approved.policy_bundle_id,
        source="docs/method-conformance/pilot-obligations.yaml (approved)",
        contracts={approved.phase: approved},
    )
    service = MethodConformanceService(selection)
    readiness = [
        ReadinessTarget(
            target_type="PHASE_EXIT",
            target_id=f"{PILOT_SCOPE_RECORD}/phase10",
        )
    ]
    evaluation = service.evaluation(
        approved.phase, assembly.context, requested_readiness=readiness
    )
    if evaluation is None:
        report["status"] = "refused"
        report["reason_codes"] = ["CONTRACT_UNAVAILABLE"]
        _emit(report, output)
        return 2
    report["phase_contract"] = service.phase_contract(approved.phase)
    disposition = {
        "evaluation_key": evaluation.evaluation_key,
        "assessment_coverage": evaluation.assessment_coverage,
        "evaluation_state": evaluation.evaluation_state,
        "conformance_verdict": evaluation.conformance_verdict,
        "assessed_ids": list(evaluation.assessed_ids),
        "unassessed_ids": list(evaluation.unassessed_ids),
        "failed_ids": list(evaluation.failed_ids),
        "indeterminate_ids": list(evaluation.indeterminate_ids),
        "errored_ids": list(evaluation.errored_ids),
        "not_applicable_ids": list(evaluation.not_applicable_ids),
        "results": [result.as_dict() for result in evaluation.results],
        "readiness": [block.as_dict() for block in evaluation.readiness],
    }
    report["status"] = "evaluated"
    report["disposition"] = disposition
    report["evaluation_count"] = service.evaluation_count
    report["increment_status"] = service.increment_status(
        approved.phase, assembly.context, requested_readiness=readiness
    )
    report["method_gaps"] = service.method_gaps(approved.phase, assembly.context)
    report["next_obligation"] = service.next_obligation(
        approved.phase, assembly.context
    )
    _emit(report, output)

    # Compact human summary.
    print(f"evaluation_key: {evaluation.evaluation_key}")
    print(
        f"aggregate: {evaluation.assessment_coverage} / "
        f"{evaluation.evaluation_state} / {evaluation.conformance_verdict}"
    )
    for result in evaluation.results:
        if result.subject_id is None:
            print(
                f"  {result.unit_id}: {result.coverage} / {result.state} / "
                f"{result.verdict} {list(result.reason_codes)}"
            )
    print("readiness:", json.dumps([b.as_dict() for b in evaluation.readiness]))
    return 0


def _emit(report: dict, output: Path | None) -> None:
    if output is not None:
        output.write_text(json.dumps(report, indent=2, sort_keys=False))
        print(f"wrote {output}")


if __name__ == "__main__":
    sys.exit(main())
