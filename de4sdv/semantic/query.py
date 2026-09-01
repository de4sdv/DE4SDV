"""Agent-independent, revision-bound semantic query service.

This module is the reusable application layer exposed by CLI, MCP, or any other
client protocol. It contains no MCP- or Hermes-specific behavior. All engineering
relationships come from the ontology contract and :class:`SemanticTraversal`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from de4sdv.sysml_api.errors import ApiError, RevisionMismatchError
from de4sdv.sysml_api.identity import IdentityResolution, resolve_identity
from de4sdv.sysml_api.repository import SysMLRepository, element_id, reference_ids
from de4sdv.sysml_api.revisions import RevisionBinding

from .api_binding import OntologyApiBinder
from .impact import ImpactService
from .kernel_contract import KernelContract
from .traversal import SemanticTraversal, TraversalHop


@dataclass
class SemanticQueryService:
    """Compact read-only semantic queries against one validated API revision."""

    repository: SysMLRepository
    binding: RevisionBinding
    contract: KernelContract
    binder: OntologyApiBinder
    traversal: SemanticTraversal
    impact_service: ImpactService
    expected_git_revision: str
    _element_cache: list[dict[str, Any]] | None = field(
        default=None, init=False, repr=False
    )

    def _revision(self) -> dict[str, str]:
        return {
            "git_commit": self.binding.git_commit,
            "sysml_project_id": self.binding.sysml_project_id,
            "sysml_commit_id": self.binding.sysml_commit_id,
            "binding_status": self.binding.status(self.expected_git_revision),
            "scope": self.binding.scope,
        }

    def _provenance(self) -> list[dict[str, str]]:
        return [
            {
                "authority": "authoritative",
                "source": f"git://{self.binding.git_repository}/{self.binding.git_commit}",
            },
            {
                "authority": "authoritative",
                "source": (
                    f"sysml://{self.binding.sysml_project_id}/"
                    f"{self.binding.sysml_commit_id}"
                ),
            },
            {
                "authority": "authoritative",
                "source": str(self.contract.source),
            },
            {"authority": "derived", "source": "de4sdv.semantic.query"},
        ]

    def _require_current_full_model(self) -> None:
        self.binding.require_current(self.expected_git_revision)
        if self.binding.scope != "full-model":
            raise RevisionMismatchError(
                "semantic current-baseline claim requires a validated full-model "
                f"binding, got scope {self.binding.scope!r}"
            )

    def _elements(self) -> list[dict[str, Any]]:
        self._require_current_full_model()
        if self._element_cache is None:
            self._element_cache = self.repository.list_elements(
                self.binding.sysml_project_id, self.binding.sysml_commit_id
            )
        return self._element_cache

    def _resolve(
        self, identifier: str, *, expected_type: str | None = None
    ) -> tuple[IdentityResolution, list[dict[str, Any]]]:
        elements = self._elements()
        return (
            resolve_identity(identifier, elements, expected_type=expected_type),
            elements,
        )

    def _compact_element(self, element: dict[str, Any]) -> dict[str, Any]:
        candidate_id = element_id(element)
        if candidate_id is None:
            raise ValueError("semantic result element has no API UUID")
        return {
            "element_id": candidate_id,
            "sysml_type": str(element.get("@type") or ""),
            "declared_name": element.get("declaredName") or element.get("name"),
            "qualified_name": element.get("qualifiedName"),
            "source_uri": (
                f"sysml://{self.binding.sysml_project_id}/"
                f"{self.binding.sysml_commit_id}/{candidate_id}"
            ),
        }

    def _edge(self, hop: TraversalHop) -> dict[str, Any]:
        source_id = element_id(hop.source)
        target_id = element_id(hop.target)
        api_object_id = element_id(hop.api_object)
        if source_id is None or target_id is None or api_object_id is None:
            raise ValueError("semantic traversal hop is missing an API UUID")
        return {
            "source": source_id,
            "predicate": hop.predicate,
            "target": target_id,
            "strategy": hop.strategy,
            "semantic_strength": hop.semantic_strength,
            "api_object_id": api_object_id,
            "api_object_type": str(hop.api_object.get("@type") or ""),
            "provenance": (
                f"sysml://{self.binding.sysml_project_id}/"
                f"{self.binding.sysml_commit_id}/{api_object_id}"
            ),
        }

    def _mapped_predicates(self) -> list[str]:
        """Return only ontology relationships with executable SysML mappings."""
        return sorted(
            name
            for name, value in self.contract.relationships.items()
            if isinstance(value, dict)
            and isinstance(value.get("sysml_mapping"), dict)
        )

    def model_status(self) -> dict[str, Any]:
        """Report whether this runtime can make an exact current-baseline claim."""
        status = self.binding.status(self.expected_git_revision)
        current = status == "synchronized" and self.binding.scope == "full-model"
        reasons: list[str] = []
        if status != "synchronized":
            reasons.append(f"binding status is {status}")
        if self.binding.scope != "full-model":
            reasons.append(f"binding scope is {self.binding.scope}, not full-model")
        gaps: list[dict[str, str]] = [
            {"category": "runtime-binding", "reason": reason} for reason in reasons
        ]
        element_count: int | None = None
        if current:
            try:
                elements = self._elements()
                element_count = len(elements)
            except ApiError as exc:
                current = False
                gaps.append(
                    {
                        "category": "runtime-api",
                        "reason": f"Bound SysML API revision is unavailable: {exc}",
                    }
                )
        return {
            "query": "model_status",
            "current_baseline": current,
            "read_only": True,
            "revision": self._revision(),
            "element_count": element_count,
            "gaps": gaps,
            "provenance": self._provenance(),
        }

    def resolve_element(
        self, identifier: str, *, expected_type: str | None = None
    ) -> dict[str, Any]:
        resolution, _ = self._resolve(identifier, expected_type=expected_type)
        return {
            "query": "resolve_element",
            "identifier": identifier,
            "resolution_level": resolution.level,
            "element": self._compact_element(resolution.element),
            "revision": self._revision(),
            "gaps": [],
            "provenance": self._provenance(),
        }

    def inspect_element(self, identifier: str) -> dict[str, Any]:
        resolution, elements = self._resolve(identifier)
        item = resolution.element
        by_id = {
            candidate_id: candidate
            for candidate in elements
            if (candidate_id := element_id(candidate)) is not None
        }
        documentation: list[str] = []
        for document_id in reference_ids(item.get("documentation")):
            document = by_id.get(document_id, {})
            body = document.get("body") or document.get("bodyText")
            if body:
                documentation.append(str(body))
        references = sorted(
            {
                reference
                for key, value in item.items()
                if key not in {"@id", "elementId", "id"}
                for reference in reference_ids(value)
            }
        )
        compact = self._compact_element(item)
        compact.update(
            {
                "documentation": documentation,
                "referenced_element_ids": references,
            }
        )
        return {
            "query": "inspect_element",
            "identifier": identifier,
            "resolution_level": resolution.level,
            "element": compact,
            "revision": self._revision(),
            "gaps": (
                []
                if documentation
                else [
                    {
                        "category": "documentation",
                        "reason": "No API-resident documentation is attached to the resolved element.",
                    }
                ]
            ),
            "provenance": self._provenance(),
        }

    def semantic_neighbors(
        self, identifier: str, *, predicates: list[str] | None = None
    ) -> dict[str, Any]:
        resolution, elements = self._resolve(identifier)
        source = resolution.element
        selected = predicates or self._mapped_predicates()
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        gaps: list[dict[str, str]] = []
        for predicate in selected:
            # Enforces ontology declaration and rejects unsupported names.
            self.contract.relationship_mapping(predicate)
            hops = self.traversal.traverse(predicate, source, elements)
            if not hops:
                gaps.append(
                    {
                        "category": predicate,
                        "reason": (
                            "No ontology-mapped native relationship was found from "
                            "the resolved element in the bound API revision."
                        ),
                    }
                )
            for hop in hops:
                target_id = element_id(hop.target)
                if target_id is None:
                    raise ValueError("semantic neighbor has no API UUID")
                nodes[target_id] = self._compact_element(hop.target)
                edges.append(self._edge(hop))
        return {
            "query": "semantic_neighbors",
            "root": {
                **self._compact_element(source),
                "resolution_level": resolution.level,
            },
            "nodes": sorted(nodes.values(), key=lambda value: value["element_id"]),
            "edges": sorted(
                edges,
                key=lambda edge: (
                    edge["source"], edge["predicate"], edge["target"]
                ),
            ),
            "revision": self._revision(),
            "gaps": gaps,
            "provenance": self._provenance(),
        }

    def impact(self, identifier: str) -> dict[str, Any]:
        self._require_current_full_model()
        return self.impact_service.impact(
            identifier, git_revision=self.expected_git_revision
        )

    def trace(
        self, source_identifier: str, target_identifier: str, *, max_depth: int = 4
    ) -> dict[str, Any]:
        if max_depth < 1 or max_depth > 8:
            raise ValueError("max_depth must be between 1 and 8")
        source_resolution, elements = self._resolve(source_identifier)
        target_resolution = resolve_identity(target_identifier, elements)
        source_id = element_id(source_resolution.element)
        target_id = element_id(target_resolution.element)
        if source_id is None or target_id is None:
            raise ValueError("trace endpoint has no API UUID")
        by_id = {
            candidate_id: item
            for item in elements
            if (candidate_id := element_id(item)) is not None
        }
        predicates = self._mapped_predicates()
        frontier: list[tuple[str, list[dict[str, Any]]]] = [(source_id, [])]
        visited = {source_id}
        path: list[dict[str, Any]] | None = None
        while frontier:
            current_id, current_path = frontier.pop(0)
            if len(current_path) >= max_depth:
                continue
            current = by_id[current_id]
            for predicate in predicates:
                for hop in self.traversal.traverse(predicate, current, elements):
                    edge = self._edge(hop)
                    next_id = edge["target"]
                    candidate_path = [*current_path, edge]
                    if next_id == target_id:
                        path = candidate_path
                        frontier = []
                        break
                    if next_id not in visited:
                        visited.add(next_id)
                        frontier.append((next_id, candidate_path))
                if path is not None:
                    break
            if path is not None:
                break
        if path is None:
            return {
                "query": "trace",
                "source": self._compact_element(source_resolution.element),
                "target": self._compact_element(target_resolution.element),
                "path": [],
                "revision": self._revision(),
                "gaps": [
                    {
                        "category": "semantic-trace",
                        "reason": (
                            "No path using ontology-declared semantic mappings was "
                            f"found within depth {max_depth}."
                        ),
                    }
                ],
                "provenance": self._provenance(),
            }
        return {
            "query": "trace",
            "source": self._compact_element(source_resolution.element),
            "target": self._compact_element(target_resolution.element),
            "path": path,
            "revision": self._revision(),
            "gaps": [],
            "provenance": self._provenance(),
        }

    def verification_coverage(self, requirement_identifier: str) -> dict[str, Any]:
        report = self.impact(requirement_identifier)
        verification_ids = {
            edge["target"]
            for edge in report["edges"]
            if edge["predicate"] == "verifiedBy"
        }
        verified_evidence_ids = {
            edge["source"]
            for edge in report["edges"]
            if edge["predicate"] == "verifiedBy"
        }
        evidence_ids = {
            edge["target"]
            for edge in report["edges"]
            if edge["predicate"] == "hasRelevantEvidenceContract"
        }
        nodes_by_id = {node["element_id"]: node for node in report["nodes"]}
        verification_gaps = [
            gap for gap in report["gaps"] if gap["category"] == "verification"
        ]
        unverified_evidence_ids = evidence_ids - verified_evidence_ids
        if unverified_evidence_ids and verification_ids:
            status = "partial"
            verification_gaps.append(
                {
                    "category": "verification",
                    "reason": (
                        "No native verification relationship covers evidence "
                        "contracts: " + ", ".join(sorted(unverified_evidence_ids))
                    ),
                }
            )
        elif verification_ids and not verification_gaps:
            status = "covered"
        elif verification_ids:
            status = "partial"
        else:
            status = "uncovered"
        return {
            "query": "verification_coverage",
            "requirement": report["root"],
            "status": status,
            "evidence_contracts": [
                nodes_by_id[candidate]
                for candidate in sorted(evidence_ids)
                if candidate in nodes_by_id
            ],
            "verification_cases": [
                nodes_by_id[candidate]
                for candidate in sorted(verification_ids)
                if candidate in nodes_by_id
            ],
            "unverified_evidence_contracts": [
                nodes_by_id[candidate]
                for candidate in sorted(unverified_evidence_ids)
                if candidate in nodes_by_id
            ],
            "verification_edges": [
                edge for edge in report["edges"] if edge["predicate"] == "verifiedBy"
            ],
            "revision": report["revision"],
            "gaps": verification_gaps,
            "provenance": report["provenance"],
        }
