"""API-backed semantic impact query service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from de4sdv.sysml_api.identity import resolve_identity
from de4sdv.sysml_api.repository import SysMLRepository, element_id
from de4sdv.sysml_api.revisions import RevisionBinding

from .api_binding import OntologyApiBinder
from .kernel_contract import KernelContract
from .traversal import SemanticTraversal, TraversalHop


@dataclass
class ImpactService:
    """Answer revision-bound requirement impact against fixture or full model."""

    repository: SysMLRepository
    binding: RevisionBinding
    contract: KernelContract
    binder: OntologyApiBinder
    traversal: SemanticTraversal

    def impact(self, identifier: str, *, git_revision: str) -> dict[str, Any]:
        self.binding.require_current(git_revision)
        project_id = self.binding.sysml_project_id
        commit_id = self.binding.sysml_commit_id
        elements = self.repository.list_elements(project_id, commit_id)
        resolution = resolve_identity(
            identifier, elements, expected_type="RequirementUsage"
        )
        root = resolution.element
        root_id = element_id(root)
        if root_id is None:
            raise ValueError("resolved requirement has no API UUID")
        requirement_binding = self.binder.bind_class("Requirement")

        nodes: dict[str, dict[str, Any]] = {}
        edges: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        gaps: list[dict[str, str]] = []

        def add_node(
            element: dict[str, Any], semantic_type: str, category: str
        ) -> dict[str, Any]:
            candidate_id = element_id(element)
            if candidate_id is None:
                raise ValueError("impact node has no API UUID")
            node = {
                "element_id": candidate_id,
                "semantic_type": semantic_type,
                "sysml_type": str(element.get("@type") or ""),
                "declared_name": element.get("declaredName") or element.get("name"),
                "qualified_name": element.get("qualifiedName"),
                "category": category,
                "source_uri": f"sysml://{project_id}/{commit_id}/{candidate_id}",
            }
            nodes[candidate_id] = node
            return node

        def add_hop(hop: TraversalHop, semantic_type: str, category: str) -> None:
            source_hop_id = element_id(hop.source)
            target_hop_id = element_id(hop.target)
            api_object_id = element_id(hop.api_object)
            if source_hop_id is None or target_hop_id is None or api_object_id is None:
                raise ValueError("semantic API hop is missing an exact UUID")
            add_node(hop.target, semantic_type, category)
            edge = {
                "source": source_hop_id,
                "predicate": hop.predicate,
                "target": target_hop_id,
                "strategy": hop.strategy,
                "semantic_strength": hop.semantic_strength,
                "api_object_id": api_object_id,
                "api_object_type": str(hop.api_object.get("@type") or ""),
                "provenance": (
                    f"sysml://{project_id}/{commit_id}/{api_object_id}"
                ),
            }
            edges[(source_hop_id, hop.predicate, target_hop_id, api_object_id)] = edge

        root_node = add_node(root, "Requirement", "requirement")

        architecture_hops = self.traversal.traverse("realizedBy", root, elements)
        for hop in architecture_hops:
            add_hop(hop, "ArchitectureElement", "architecture")
        if not architecture_hops:
            gaps.append(
                {
                    "category": "architecture",
                    "reason": (
                        "No ontology-mapped AllocationUsage connects this requirement "
                        "to an architecture element in the bound API revision."
                    ),
                }
            )

        subject_hops = self.traversal.traverse("hasSubject", root, elements)
        for hop in subject_hops:
            add_hop(hop, "MemberProduct", "product-line")
        if not subject_hops:
            gaps.append(
                {
                    "category": "product-line",
                    "reason": "The requirement has no API subjectParameter member-product reference.",
                }
            )

        evidence_hops = self.traversal.traverse(
            "hasRelevantEvidenceContract", root, elements
        )
        for evidence_hop in evidence_hops:
            add_hop(evidence_hop, "EvidenceContract", "evidence")
            verification_hops = self.traversal.traverse(
                "verifiedBy", evidence_hop.target, elements
            )
            for verification_hop in verification_hops:
                add_hop(verification_hop, "VerificationCase", "verification")
        if not evidence_hops:
            gaps.append(
                {
                    "category": "evidence",
                    "reason": "No incoming relevance Dependency links an evidence contract to this requirement.",
                }
            )
        if evidence_hops and not any(
            node["category"] == "verification" for node in nodes.values()
        ):
            gaps.append(
                {
                    "category": "verification",
                    "reason": "No VerificationCaseUsage references the affected evidence contracts.",
                }
            )

        gaps.append(
            {
                "category": "evidence-artifact",
                "reason": (
                    "EvidenceArtifact is external in the ontology; this API query "
                    "reports API-resident evidence contracts only."
                ),
            }
        )

        return {
            "query": "impact",
            "revision": {
                "git_commit": self.binding.git_commit,
                "sysml_project_id": project_id,
                "sysml_commit_id": commit_id,
                "binding_status": "synchronized",
                "scope": self.binding.scope,
            },
            "root": {**root_node, "resolution_level": resolution.level},
            "ontology_bindings": {
                "Requirement": {
                    "element_id": requirement_binding.sysml.element_id,
                    "sysml_type": requirement_binding.sysml.type,
                    "qualified_name": requirement_binding.sysml.qualified_name,
                    "kernel_file": requirement_binding.kernel.file,
                    "kernel_declaration": requirement_binding.kernel.declaration,
                }
            },
            "nodes": sorted(nodes.values(), key=lambda node: node["element_id"]),
            "edges": sorted(
                edges.values(),
                key=lambda edge: (
                    edge["source"], edge["predicate"], edge["target"]
                ),
            ),
            "gaps": gaps,
            "provenance": [
                {
                    "authority": "authoritative",
                    "source": f"git://{self.binding.git_repository}/{self.binding.git_commit}",
                },
                {
                    "authority": "authoritative",
                    "source": f"sysml://{project_id}/{commit_id}",
                },
                {
                    "authority": "authoritative",
                    "source": str(self.contract.source),
                },
                {
                    "authority": "derived",
                    "source": "de4sdv.semantic.impact",
                },
            ],
            "claims": {
                "dependency_semantics": (
                    "relevance only; not verification, satisfaction, or compliance"
                )
            },
        }
