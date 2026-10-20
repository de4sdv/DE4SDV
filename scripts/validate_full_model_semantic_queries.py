#!/usr/bin/env python3
"""Exercise production API semantic queries across distinct model concerns, and the successor parity.

The successor parity (with ``--export``, as the privileged run passes it) is the
exact-revision evidence the ``allocatedTo`` forward obligations of
``de4sdv/semantic/contract-data/kernel-vocabulary-admission.yaml`` ask for:
over the API revision this run imported, the production runtime must serve
exactly the ``allocatedTo`` and ``hasValidationScenario`` facts that the
export it imported holds, read as the PR Method Check reads them (the export
snapshot, kernel identity re-validated from the export) and as the method
reads them; and the typed allocation ends must close
(:mod:`de4sdv.semantic.successor_parity`). A failed parity writes the report
and exits 1, so the privileged run fails and no deploy takes its evidence.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.sysml_api.revisions import RevisionBinding


@dataclass(frozen=True)
class SemanticQueryCase:
    identifier: str
    concern: str


QUERY_CASES = (
    SemanticQueryCase(
        "reqCommandEmergencyBraking",
        "AEBS braking-command change impact",
    ),
    SemanticQueryCase(
        "reqProvideMiddlewareSignalAccess",
        "middleware signal-access design input",
    ),
    SemanticQueryCase(
        "reqAuthenticateServiceBinding",
        "middleware service-binding security boundary",
    ),
)


def _json_text(value: object) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def evidence_contract_state(braking: dict[str, Any]) -> str:
    """The hasRelevantEvidenceContract state under the model authority.

    Owner decision 5 (2026-10-07): the ``hasRelevantEvidenceContract``
    discriminator is adopted (range = the EvidenceContract type closure), so
    the braking requirement must expose at least one resolved
    evidence-contract edge; a runtime that still blocks the range is a
    refusal, not an ordinary absence.
    """
    evidence_edges = [
        edge
        for edge in braking["edges"]
        if edge["predicate"] == "hasRelevantEvidenceContract"
    ]
    if not evidence_edges:
        raise RuntimeError(
            "model authority: reqCommandEmergencyBraking exposed no "
            "hasRelevantEvidenceContract edge although the EvidenceContract "
            "discriminator is adopted"
        )
    return "resolved"


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def successor_parity(runtime: Any, export_path: Path, git_commit: str) -> dict[str, Any]:
    """The successor parity of the imported API revision against the imported export.

    The export is read as the export snapshot the PR Method Check evaluates
    (kernel identity validated from the export alone, ADR 0011; a refused
    export raises); the API side is the production runtime's own traversal
    over the corpus it serves (served-model check passed). An export of
    another revision raises.
    """
    from de4sdv.semantic.export_evaluation import export_view, load_export_snapshot
    from de4sdv.semantic.increment_scope import ModelView
    from de4sdv.semantic.successor_parity import parity_report

    snapshot = load_export_snapshot(Path(export_path), root=ROOT)
    if snapshot.revision.git_commit != git_commit:
        raise RuntimeError(
            f"the export names revision {snapshot.revision.git_commit!r}, not the checkout {git_commit}")
    api = ModelView(runtime._elements(), runtime.traversal)
    return parity_report(export_view(snapshot, root=ROOT), api)


def run_queries(
    *, api_url: str, binding_path: Path, semantic_report_path: Path,
    export_path: Path | None = None,
) -> dict[str, Any]:
    from de4sdv.semantic.deployment_runtime import build_deployment_runtime

    git_commit = _git_head()
    binding = RevisionBinding.load(binding_path)
    binding.require_current(git_commit)
    semantic_report = json.loads(semantic_report_path.read_text(encoding="utf-8"))
    expected_revision = (
        semantic_report.get("git_commit"),
        semantic_report.get("sysml_project_id"),
        semantic_report.get("sysml_commit_id"),
    )
    actual_revision = (
        binding.git_commit,
        binding.sysml_project_id,
        binding.sysml_commit_id,
    )
    if expected_revision != actual_revision:
        raise RuntimeError(
            f"semantic report/binding revision mismatch: {expected_revision} != {actual_revision}"
        )
    if not semantic_report.get("kernel_binding_validation", {}).get("passed"):
        raise RuntimeError("kernel binding validation report is not passed")
    if int(semantic_report.get("source_document_count", 0)) < 3:
        raise RuntimeError("semantic report does not prove a multi-document full baseline")

    if semantic_report.get("semantic_authority") != binding.semantic_authority.to_dict():
        raise RuntimeError(
            "semantic report semantic authority does not match the validated binding"
        )
    # The production construction: the startup check (exact commit, clean
    # tree, sai- identity, served-model record), then the deployed services.
    runtime = build_deployment_runtime(
        ROOT, api_url=api_url, binding_path=binding_path, expected_git_revision=git_commit,
    )
    service = runtime.impact_service
    results: list[dict[str, Any]] = []
    allowed_strengths = {
        "allocation",
        "native-verification",
        "native-reference",
        "relevance",
    }
    for case in QUERY_CASES:
        impact = service.impact(case.identifier, git_revision=git_commit)
        if impact["revision"]["scope"] != "full-model":
            raise RuntimeError(f"{case.identifier} did not use a full-model binding")
        if impact["root"]["declared_name"] != case.identifier:
            raise RuntimeError(f"{case.identifier} resolved to the wrong API object")
        invalid_strengths = {
            edge["semantic_strength"] for edge in impact["edges"]
        } - allowed_strengths
        if invalid_strengths:
            raise RuntimeError(
                f"{case.identifier} crossed unsupported semantic strengths: "
                f"{sorted(invalid_strengths)}"
            )
        if not isinstance(impact.get("gaps"), list):
            raise RuntimeError(f"{case.identifier} did not report explicit gaps")
        results.append(
            {
                "identifier": case.identifier,
                "concern": case.concern,
                "impact": impact,
            }
        )

    braking = next(
        result["impact"]
        for result in results
        if result["identifier"] == "reqCommandEmergencyBraking"
    )
    evidence_state = evidence_contract_state(braking)
    subject_edges = [
        edge
        for edge in braking["edges"]
        if edge["predicate"] == "hasSubject"
        and edge["strategy"] == "subject-membership"
    ]
    if not subject_edges:
        raise RuntimeError(
            "imported reqCommandEmergencyBraking did not expose its native "
            "SubjectMembership product-line subject"
        )
    verification_edges = [
        edge
        for edge in braking["edges"]
        if edge["predicate"] == "verifiedBy"
        and edge["strategy"] == "verification-membership"
    ]
    gap_categories = {gap["category"] for gap in braking["gaps"]}
    if "product-line" in gap_categories:
        raise RuntimeError(
            "native subject membership resolved but was still reported as a gap"
        )
    if not verification_edges:
        # The pinned exporter (Syside 0.10.3) does not serialize `verify`
        # statements from AEBS verification objectives as
        # RequirementVerificationMembership objects; until upstream resolves
        # that, the AEBS verification path is reported as an explicit gap
        # instead of being inferred by name.
        print(
            "NOTE: verification-case links for the AEBS evidence contracts are "
            "not present in the serialized model; reported as an explicit gap."
        )

    root_ids = {result["impact"]["root"]["element_id"] for result in results}
    if len(root_ids) != len(results):
        raise RuntimeError("semantic query cases did not resolve to distinct API UUIDs")
    report = {
        "schema": "de4sdv-full-model-semantic-query-coverage/v2",
        "git_commit": git_commit,
        "sysml_project_id": binding.sysml_project_id,
        "sysml_commit_id": binding.sysml_commit_id,
        "concern_count": len({case.concern for case in QUERY_CASES}),
        "results": results,
        "semantic_authority": runtime.authority_status(),
        "evidence_contract_state": evidence_state,
    }
    if export_path is not None:
        report["successor_parity"] = successor_parity(runtime, Path(export_path), git_commit)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--semantic-report", type=Path, required=True)
    parser.add_argument("--export", type=Path, required=True,
                        help="the export this run imported (the successor parity reads it)")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_queries(
        api_url=args.api_url,
        binding_path=args.binding,
        semantic_report_path=args.semantic_report,
        export_path=args.export,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    parity = result.get("successor_parity") or {}
    print(
        json.dumps(
            {
                "concern_count": result["concern_count"],
                "successor_parity": bool(parity.get("passed")),
                "output": str(args.output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    if parity.get("passed") is not True:
        sections = {**(parity.get("relations") or {}),
                    "allocation_end_closure": parity.get("allocation_end_closure") or {}}
        for name, section in sections.items():
            for check, ok in (section.get("checks") or {}).items():
                if not ok:
                    print(f"FAIL successor parity {name}: {check}", file=sys.stderr)
        print("successor parity failed: the imported API revision does not serve the export's facts",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
