#!/usr/bin/env python3
"""Exercise production API semantic queries across distinct model concerns."""

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

from de4sdv.semantic.api_binding import OntologyApiBinder
from de4sdv.semantic.impact import ImpactService
from de4sdv.semantic.kernel_contract import KernelContract
from de4sdv.semantic.traversal import SemanticTraversal
from de4sdv.sysml_api.client import ApiClient
from de4sdv.sysml_api.repository import SysMLRepository, reference_ids, element_id
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


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def run_queries(
    *, api_url: str, binding_path: Path, semantic_report_path: Path
) -> dict[str, Any]:
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
    if not semantic_report.get("ontology", {}).get("passed"):
        raise RuntimeError("ontology report is not passed")
    if int(semantic_report.get("source_document_count", 0)) < 3:
        raise RuntimeError("semantic report does not prove a multi-document full baseline")

    repository = SysMLRepository(ApiClient(api_url, timeout=600.0))
    contract = KernelContract.load(
        ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
    )
    binding.require_ontology(contract.identity)
    if semantic_report.get("ontology_identity") != binding.ontology.to_dict():
        raise RuntimeError(
            "semantic report ontology identity does not match the validated binding"
        )
    service = ImpactService(
        repository=repository,
        binding=binding,
        contract=contract,
        binder=OntologyApiBinder(
            contract,
            repository,
            project_id=binding.sysml_project_id,
            commit_id=binding.sysml_commit_id,
        ),
        traversal=SemanticTraversal(contract),
    )
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
    evidence_edges = [
        edge
        for edge in braking["edges"]
        if edge["predicate"] == "hasRelevantEvidenceContract"
    ]
    if len(evidence_edges) < 3:
        raise RuntimeError(
            "imported reqCommandEmergencyBraking did not retain its three modeled "
            "evidence-contract relevance links"
        )
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
    evidence_ids = {
        edge["target"]
        for edge in braking["edges"]
        if edge["predicate"] == "hasRelevantEvidenceContract"
    }
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
    return {
        "schema": "de4sdv-full-model-semantic-query-coverage/v1",
        "git_commit": git_commit,
        "sysml_project_id": binding.sysml_project_id,
        "sysml_commit_id": binding.sysml_commit_id,
        "concern_count": len({case.concern for case in QUERY_CASES}),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--semantic-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_queries(
        api_url=args.api_url,
        binding_path=args.binding,
        semantic_report_path=args.semantic_report,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "concern_count": result["concern_count"],
                "output": str(args.output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
