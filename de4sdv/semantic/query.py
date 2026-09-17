"""Agent-independent, revision-bound semantic query service.

This module is the reusable application layer exposed by CLI, MCP, or any other
client protocol. It contains no MCP- or Hermes-specific behavior. All engineering
relationships come from the ontology contract and :class:`SemanticTraversal`.

Lane C adds the four method-conformance surfaces specified by the frozen
baseline Section 13 (``phase_contract``, ``increment_status``, ``method_gaps``,
``next_obligation``). They reuse this service and the bound revision; no
parallel graph or second service is introduced. The three evaluation
projections share one canonical evaluation identity through
:class:`~de4sdv.semantic.method_evaluator.MethodConformanceService`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from de4sdv.sysml_api.errors import ApiError
from de4sdv.sysml_api.identity import IdentityResolution, resolve_identity
from de4sdv.sysml_api.repository import SysMLRepository, element_id, reference_ids
from de4sdv.sysml_api.revisions import RevisionBinding

from .api_binding import OntologyApiBinder
from .authority_ids import LEGACY_AUTHORITY_ID
from .impact import ImpactService
from .kernel_contract import KernelContract
from .method_evaluator import (
    EvaluationContext,
    MethodConformanceService,
    ReadinessTarget,
    ReadinessBlock,
)
from .traversal import (
    EVIDENCE_CONTRACT_BLOCKED_REASON,
    SemanticTraversal,
    TraversalHop,
)


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
    method_conformance: MethodConformanceService | None = field(default=None)
    method_context_provider: Callable[[], EvaluationContext] | None = field(
        default=None
    )
    semantic_authority_id: str = LEGACY_AUTHORITY_ID
    _element_cache: list[dict[str, Any]] | None = field(
        default=None, init=False, repr=False
    )
    _impact_cache: dict[str, dict[str, Any]] = field(
        default_factory=dict, init=False, repr=False
    )

    def _revision(self) -> dict[str, Any]:
        return {
            "git_commit": self.binding.git_commit,
            "sysml_project_id": self.binding.sysml_project_id,
            "sysml_commit_id": self.binding.sysml_commit_id,
            "binding_status": self.binding.status(self.expected_git_revision),
            "scope": self.binding.scope,
            "ontology": self.binding.ontology.to_dict(),
        }

    def _provenance(self) -> list[dict[str, str]]:
        if self.semantic_authority_id != LEGACY_AUTHORITY_ID:
            # Candidate authority path: the ontology is the ingestion
            # compatibility identity, never the semantic authority for the
            # migrated set; semantics come from the Projection, mechanics
            # from the Profile.
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
                    "authority": "semantic-authority",
                    "source": f"projection://{self.semantic_authority_id}",
                },
                {
                    "authority": "representation-authority",
                    "source": f"profile://{self.semantic_authority_id}",
                },
                {
                    "authority": "compatibility",
                    "source": (
                        f"git://{self.binding.git_repository}/{self.binding.git_commit}/"
                        f"{self.binding.ontology.path}"
                    ),
                    "sha256": self.binding.ontology.sha256,
                },
                {"authority": "derived", "source": "de4sdv.semantic.query"},
            ]
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
                "source": (
                    f"git://{self.binding.git_repository}/{self.binding.git_commit}/"
                    f"{self.binding.ontology.path}"
                ),
                "sha256": self.binding.ontology.sha256,
            },
            {"authority": "derived", "source": "de4sdv.semantic.query"},
        ]

    def _require_valid_revision(self) -> None:
        self.binding.require_current(self.expected_git_revision)
        self.binding.require_ontology(self.contract.identity)

    def _elements(self) -> list[dict[str, Any]]:
        self._require_valid_revision()
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
            **(
                {"witness": hop.witness}
                if getattr(hop, "witness", None)
                else {}
            ),
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
        ontology_current = self.contract.identity == self.binding.ontology
        current = (
            status == "synchronized"
            and self.binding.scope == "full-model"
            and ontology_current
        )
        reasons: list[str] = []
        if status != "synchronized":
            reasons.append(f"binding status is {status}")
        if self.binding.scope != "full-model":
            reasons.append(f"binding scope is {self.binding.scope}, not full-model")
        if not ontology_current:
            reasons.append(
                "ontology contract does not match the identity recorded in the binding"
            )
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
        payload: dict[str, Any] = {
            "query": "model_status",
            "current_baseline": current,
            "read_only": True,
            "revision": self._revision(),
            "element_count": element_count,
            "gaps": gaps,
            "provenance": self._provenance(),
            "semantic_authority": self._semantic_authority(),
        }
        return payload

    def _semantic_authority(self) -> dict[str, Any]:
        """Deployment provenance: which semantic authority produced answers.

        Always present, so a deployed service can be inspected for
        ``legacy`` vs ``o3`` without guessing from the absence of a block.
        The O3 block identifies the exact bundle; the bundle was verified
        against this exact revision and revision binding at startup.
        """
        if self.semantic_authority_id == LEGACY_AUTHORITY_ID:
            return {
                "id": LEGACY_AUTHORITY_ID,
                "kind": "legacy",
                "note": (
                    "authored KernelContract authority (production default; "
                    "unchanged behavior)"
                ),
            }
        return {
            "id": self.semantic_authority_id,
            "kind": "o3",
            "migrated_scope": "reviewed-13-identity-subset",
            "note": (
                "explicitly selected O3 authority bundle (Semantic Projection "
                "semantics + API Representation Profile mechanics); every "
                "other identity delegates to the legacy authored "
                "KernelContract; verified against this exact revision and "
                "revision binding at startup"
            ),
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

    def _blocked_unsupported(self, predicate: str) -> dict[str, str]:
        """Structured unsupported record for one governed-blocked predicate.

        c5 integration closure (PR #249, R1): a predicate whose declared
        range is governed blocked cannot be evaluated, so its zero edges are
        NOT ordinary supported absence. The record shape is the reusable
        blocked/unsupported representation shared by the query surfaces.
        """
        return {
            "predicate": predicate,
            "authority_state": "blocked",
            "reason": EVIDENCE_CONTRACT_BLOCKED_REASON,
        }

    def semantic_neighbors(
        self, identifier: str, *, predicates: list[str] | None = None
    ) -> dict[str, Any]:
        resolution, elements = self._resolve(identifier)
        source = resolution.element
        selected = predicates or self._mapped_predicates()
        blocked_predicates = self.traversal.blocked_predicates()
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        gaps: list[dict[str, str]] = []
        unsupported: list[dict[str, str]] = []
        for predicate in selected:
            # Enforces ontology declaration and rejects unsupported names.
            self.contract.relationship_mapping(predicate)
            if predicate in blocked_predicates:
                # Blocked governed authority: zero edges by fail-closed
                # decision, reported as unsupported rather than ordinary
                # absence (c5 correction + integration closure, PR #249).
                unsupported.append(self._blocked_unsupported(predicate))
                continue
            hops = self.traversal.traverse(predicate, source, elements)
            if not hops:
                gaps.append(
                    {
                        "category": predicate,
                        "reason": (
                            "No ontology-mapped native relationship was found "
                            "from the resolved element in the bound API revision."
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
            # Mixed outcomes are allowed and expected: evaluated predicates
            # report ordinary gaps; blocked predicates appear here with the
            # reviewed missing-identity reason. ``semantic_status`` is
            # ``complete`` only when every requested predicate was evaluated.
            "semantic_status": (
                "incomplete" if unsupported else "complete"
            ),
            "unsupported_predicates": unsupported,
            "gaps": gaps,
            "provenance": self._provenance(),
        }

    def impact(self, identifier: str) -> dict[str, Any]:
        resolution, _ = self._resolve(identifier)
        root_id = element_id(resolution.element)
        if root_id is None:
            raise ValueError("impact root has no API UUID")
        if root_id not in self._impact_cache:
            self._impact_cache[root_id] = self.impact_service.impact(
                root_id, git_revision=self.expected_git_revision
            )
        return self._impact_cache[root_id]

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
        blocked_predicates = self.traversal.blocked_predicates()
        unavailable = [self._blocked_unsupported(p) for p in sorted(blocked_predicates)]
        frontier: list[tuple[str, list[dict[str, Any]]]] = [(source_id, [])]
        visited = {source_id}
        path: list[dict[str, Any]] | None = None
        while frontier:
            current_id, current_path = frontier.pop(0)
            if len(current_path) >= max_depth:
                continue
            current = by_id[current_id]
            for predicate in predicates:
                if predicate in blocked_predicates:
                    # Blocked governed authority: this predicate was not
                    # available during traversal (c5 correction, PR #249).
                    # Record it; never attribute a failed trace to it.
                    continue
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
        # ``unavailable_predicates`` distinguishes "no supported path was
        # found" from "all relevant semantic paths were fully evaluated and
        # proven absent": when blocked predicates could not participate, the
        # latter claim cannot be made (c5 integration closure, PR #249).
        unavailable_block = [
            {
                "category": "semantic-trace-unavailable",
                "reason": (
                    "Ontology-mapped predicate "
                    f"{record['predicate']} was unavailable during this "
                    "trace: " + record["reason"]
                ),
            }
            for record in unavailable
        ]
        if path is None:
            return {
                "query": "trace",
                "source": self._compact_element(source_resolution.element),
                "target": self._compact_element(target_resolution.element),
                "path": [],
                "revision": self._revision(),
                "semantic_status": (
                    "incomplete" if unavailable else "complete"
                ),
                "unsupported_predicates": unavailable,
                "gaps": [
                    {
                        "category": "semantic-trace",
                        "reason": (
                            "No path using ontology-declared semantic mappings was "
                            f"found within depth {max_depth}."
                        ),
                    }
                ]
                + unavailable_block,
                "provenance": self._provenance(),
            }
        return {
            "query": "trace",
            "source": self._compact_element(source_resolution.element),
            "target": self._compact_element(target_resolution.element),
            "path": path,
            "revision": self._revision(),
            "semantic_status": (
                "incomplete" if unavailable else "complete"
            ),
            "unsupported_predicates": unavailable,
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
        # c5 integration closure (PR #249, R1; corrected): the blocked
        # EvidenceContract range is a distinct state from evaluated absence.
        # Detection reads the STRUCTURED governed authority state from the
        # traversal's blocked-predicate source — never human-readable gap
        # prose: structured authority state -> coverage unsupported state.
        # While the range is blocked the impact evidence gap is always
        # present (the fail-closed gate emits nothing), and when the range is
        # ever unblocked this check self-corrects to False. Coverage must
        # never be reported as ordinary "uncovered" solely because no
        # EvidenceContract edges were emitted, and the missing-identity
        # reason must survive into this result.
        blocked = "hasRelevantEvidenceContract" in self.traversal.blocked_predicates()
        unsupported: list[dict[str, str]] = []
        if blocked:
            unsupported.append(self._blocked_unsupported("hasRelevantEvidenceContract"))
            verification_gaps.append(
                {
                    "category": "verification-unsupported",
                    "reason": (
                        "Verification coverage through the declared "
                        "hasRelevantEvidenceContract range cannot be assessed: "
                        + EVIDENCE_CONTRACT_BLOCKED_REASON
                    ),
                }
            )
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
        elif blocked:
            # The EvidenceContract range is blocked: coverage through it is
            # not assessable, which is a different state from an evaluated
            # absence of verification cases.
            status = "incomplete"
        else:
            status = "uncovered"
        return {
            "query": "verification_coverage",
            "requirement": report["root"],
            "status": status,
            "semantic_status": (
                "incomplete" if unsupported else "complete"
            ),
            "unsupported_predicates": unsupported,
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

    # ------------------------------------------------------------------
    # Method-conformance surfaces (frozen baseline Section 13; Lane C)
    # ------------------------------------------------------------------

    def _require_method_conformance(self) -> MethodConformanceService:
        if self.method_conformance is None:
            raise RuntimeError(
                "method-conformance evaluation is not configured for this runtime"
            )
        return self.method_conformance

    def _method_context(self) -> EvaluationContext:
        if self.method_context_provider is None:
            raise RuntimeError(
                "no method-evaluation context provider is configured for this runtime"
            )
        return self.method_context_provider()

    def phase_contract(
        self, phase: str, candidate_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Candidate-independent read of the approved phase contract.

        Method-only provenance; never a conformance verdict, and no candidate
        Git/API binding is fabricated. Optional candidate context resolves
        applicability only; obligations are never removed.
        """
        return self._require_method_conformance().phase_contract(
            phase, candidate_context
        )

    def increment_status(
        self,
        phase: str,
        *,
        requested_readiness: list[ReadinessTarget] | None = None,
    ) -> dict[str, Any]:
        """Scoped model-contract conformance projection."""
        service = self._require_method_conformance()
        return service.increment_status(
            phase,
            self._method_context(),
            requested_readiness=tuple(requested_readiness or ()),
        )

    def method_gaps(self, phase: str) -> dict[str, Any]:
        """Explicit violations, unresolved inputs, and out-of-scope obligations."""
        return self._require_method_conformance().method_gaps(
            phase, self._method_context()
        )

    def next_obligation(self, phase: str) -> dict[str, Any]:
        """Deterministic next actionable obligation (no agent assignment)."""
        return self._require_method_conformance().next_obligation(
            phase, self._method_context()
        )
