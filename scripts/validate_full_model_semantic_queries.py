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
    evidence_id = next(iter(evidence_ids)) if evidence_ids else ""
    verification_edges = [
        edge
        for edge in braking["edges"]
        if edge["predicate"] == "verifiedBy"
        and edge["strategy"] == "verification-membership"
    ]
    if not verification_edges:
        all_elements = repository.list_elements(
            binding.sysml_project_id, binding.sysml_commit_id
        )
        rvm_samples = [
            element
            for element in all_elements
            if element.get("@type") == "RequirementVerificationMembership"
        ][:3]
        by_id_all = {
            candidate_id: element
            for element in all_elements
            if (candidate_id := element_id(element)) is not None
        }
        membership_links: dict[str, list[tuple[str, str]]] = {}
        for element in all_elements:
            etype = str(element.get("@type"))
            if not etype.endswith("Membership"):
                continue
            for member_ref in reference_ids(element.get("memberElement")) + reference_ids(
                element.get("ownedMemberElement")
            ):
                for owner_ref in (
                    reference_ids(element.get("owningRelatedElement"))
                    + reference_ids(element.get("owner"))
                    + reference_ids(element.get("membershipOwningNamespace"))
                    + reference_ids(element.get("owningNamespace"))
                ):
                    membership_links.setdefault(member_ref, []).append(
                        (etype, owner_ref)
                    )
        chains = []
        for evidence_id in sorted(evidence_ids):
            frontier = [(evidence_id, 0)]
            seen = {evidence_id}
            while frontier and len(chains) < 12:
                current, depth = frontier.pop(0)
                if depth > 4:
                    continue
                for etype, owner_ref in membership_links.get(current, ()):
                    owner = by_id_all.get(owner_ref, {})
                    chains.append(
                        f"{evidence_id[:8]} -{depth}-> {etype} -> {owner_ref[:8]} "
                        f"{owner.get('@type')} {owner.get('declaredName')}"
                    )
                    if owner_ref not in seen:
                        seen.add(owner_ref)
                        frontier.append((owner_ref, depth + 1))
        rvm_total = sum(
            1 for e in all_elements if e.get("@type") == "RequirementVerificationMembership"
        )
        rvm_with_member = sum(
            1
            for e in all_elements
            if e.get("@type") == "RequirementVerificationMembership"
            and reference_ids(e.get("memberElement"))
        )
        vcu_verified = sum(
            1
            for e in all_elements
            if e.get("@type") in {"VerificationCaseUsage", "VerificationCaseDefinition"}
            and reference_ids(e.get("verifiedRequirement"))
        )
        objective_memberships = sum(
            1 for e in all_elements if e.get("@type") == "ObjectiveMembership"
        )
        raise RuntimeError(
            "imported reqCommandEmergencyBraking evidence contracts are not "
            "linked to verification cases through native relationships; "
            f"GLOBAL rvm_total={rvm_total} rvm_with_member={rvm_with_member} "
            f"vcu_nonempty_verified={vcu_verified} objective_memberships={objective_memberships}; "
            f"evidence ids: {sorted(evidence_ids)}; owner chains: "
            + " | ".join(chains[:12])
        )
    gap_categories = {gap["category"] for gap in braking["gaps"]}
    if "product-line" in gap_categories or "verification" in gap_categories:
        raise RuntimeError(
            "native subject/verification relationships resolved but were still "
            "reported as gaps: " + ", ".join(sorted(gap_categories))
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
