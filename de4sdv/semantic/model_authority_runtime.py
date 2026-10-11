"""Model-authority runtime: the model-built contract served through the live services.

The semantic authority is the model-built kernel contract
(:mod:`de4sdv.semantic.model_contract`): the live projection/profile pairs
(definitions batch 1 and 2, O2+ native/library rows, vocabulary carriers),
the frozen O2-chain records, the model-generated relationship-successor
contract and the kernel-internal declarations manifest. Its identity is the
``sai-`` semantic-authority id. There is no authored ontology, no O3 component
and no other authority: retired and refused identities answer only with
their disposition.

This module holds the facade over that contract and the traversal, query
and impact services that serve it. Production construction is
:func:`de4sdv.semantic.deployment_runtime.build_deployment_runtime`: one
startup check (exact commit, clean tree, the same ``sai-`` id recomputed from
the checkout, the served model equal to the validated export), then
:func:`assemble_model_services`. The PR Method Check builds the same facade
over the licensed export (:mod:`de4sdv.semantic.export_evaluation`).

``hasRelevantEvidenceContract`` uses the owner-adopted discriminator: its
range is the authored type closure of the validated ``EvidenceContract``
kernel root, which must contain exactly
:data:`EXPECTED_EVIDENCE_CONTRACT_DEFINITIONS` specializing definitions (the
eight AEBS evidence contracts). Any other population fails closed with
:data:`MODEL_EVIDENCE_CONTRACT_BLOCKED_REASON`.

Non-claims: serving the model-built contract is not compliance or a semantic
proof beyond the bound artifacts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from de4sdv.sysml_api.errors import IdentityNotFoundError

from .impact import ImpactService
from .kernel_contract import KernelContract, KernelFileMapping, RelationshipMapping
from .model_contract import (  # noqa: F401 — re-exported model-contract surface
    BATCH2_LAYER,
    BATCH2_LAYERS,
    DISCRIMINATED_PREDICATES,
    EVIDENCE_CONTRACT_CLASS,
    EXPECTED_EVIDENCE_CONTRACT_DEFINITIONS,
    LAYERS,
    O2_CHAIN_IDENTITIES,
    O2_CHAIN_LAYER,
    ROUTING_SCHEMA,
    LayerSpec,
    ModelAuthorityRefused,
    Provision,
    Routing,
    build_model_contract,
    canonical_json,
    compute_routing,
    generate_model_successor_contract,
    load_model_layers,
    load_register_rows,
)
from .relationship_successor import SuccessorQueryService, SuccessorTraversal

ROOT = Path(__file__).resolve().parents[2]

MODEL_AUTHORITY = "model"

MODEL_EVIDENCE_CONTRACT_BLOCKED_REASON = (
    "EvidenceContract type closure is not established at this revision: the "
    "model-authority discriminator requires the validated EvidenceContract "
    "kernel root and exactly "
    f"{EXPECTED_EVIDENCE_CONTRACT_DEFINITIONS} authored specializing "
    "requirement definitions; native verification membership alone never "
    "establishes the range."
)


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _canonical_digest(value: Any) -> str:
    return _sha256_bytes(canonical_json(value).encode("utf-8"))


def load_layers(root: Path = ROOT) -> tuple[list[dict[str, Any]], list[Provision]]:
    """Every layer of the model-built contract: (layer records, provisions)."""
    return load_model_layers(root)


def generate_successor_contract(root: Path = ROOT) -> dict[str, Any]:
    """The successor contract generated from the model (pins from the layers)."""
    return generate_model_successor_contract(root)


def _successor_names(contract: Mapping[str, Any]) -> dict[str, str]:
    """Successor relation identity -> canonical name (inverses included)."""
    names = {}
    for name, rows in contract["relations"].items():
        names[name] = name
        inverse = rows[0].get("inverse")
        if inverse:
            names[inverse] = name
    return names


def _model_routing(root: Path, records: list[dict[str, Any]], provisions: list[Provision],
                   successor: Mapping[str, Any]) -> Routing:
    chain = [p for p in provisions if p.layer == O2_CHAIN_LAYER]
    layered = [p for p in provisions if p.layer != O2_CHAIN_LAYER]
    return compute_routing(provisions=layered, successor_contract=successor,
                           register_rows=load_register_rows(root), seed=chain)


def _successor_record(contract: Mapping[str, Any]) -> dict[str, Any]:
    return {"id": contract["id"], "schema": contract["schema"],
            "sha256": _canonical_digest(contract),
            "relations": sorted(_successor_names(contract)),
            "retired": sorted(contract.get("retired") or ())}


# ---------------------------------------------------------------------------
# Runtime facade (duck-compatible with KernelContract)
# ---------------------------------------------------------------------------


class ModelAuthorityFacade:
    """The model-built contract plus its routing and the successor profile."""

    def __init__(self, *, contract: KernelContract, routing: Routing,
                 successor_contract: Mapping[str, Any], components: Mapping[str, Any]) -> None:
        if routing.duplicates:
            raise ModelAuthorityRefused("duplicate providers: " + "; ".join(routing.duplicates))
        if routing.residual:
            raise ModelAuthorityRefused("routing residual is not empty: "
                                        + ", ".join(sorted(routing.residual)))
        self._contract = contract
        self._routing = routing
        self._components = components
        self.profile = json.loads(json.dumps(dict(successor_contract)))
        self._inverse = {}
        for name, rows in self.profile["relations"].items():
            if rows[0].get("inverse"):
                self._inverse[rows[0]["inverse"]] = name
        self.identity = contract.identity
        self.source = contract.source
        #: The served semantic-authority id is the contract identity itself.
        self.authority_id = contract.identity.id
        self.binding_routes: list[dict[str, Any]] = []
        self.refused = MappingProxyType(dict(contract.refused))
        self.classes = dict(contract.classes)
        self.relationships = dict(contract.relationships)

    def provider_of(self, name: str) -> str:
        provision = self._routing.providers.get(name)
        if provision is not None:
            return provision.layer
        if name in self.refused:
            return "refused"
        return "unknown"

    def mapping(self, name: str) -> Any:
        return self._contract.mapping(name)

    def class_mapping(self, name: str) -> KernelFileMapping:
        return self._contract.class_mapping(name)

    def relationship_mapping(self, name: str) -> RelationshipMapping:
        return self._contract.relationship_mapping(name)

    def provenance(self) -> dict[str, Any]:
        layers = []
        for record in self._components["layers"]:
            if record.get("frozen"):
                layers.append({"layer": record["layer"], "frozen": True,
                               "chain_sha256": [item["sha256"] for item in record["chain"]]})
            else:
                layers.append({"layer": record["layer"],
                               "projection_sha256": record["projection"]["sha256"],
                               "profile_sha256": record["profile"]["sha256"]})
        return {
            "kind": MODEL_AUTHORITY,
            "authority_id": self.authority_id,
            "semantic_authority_id": self.identity.id,
            "layers": layers,
            "successor_contract_id": self._components["successor_contract"]["id"],
            "refused_identities": sorted(self.refused),
            "binding_routes": list(self.binding_routes),
            "status": "model-built semantic authority",
        }


# ---------------------------------------------------------------------------
# Traversal / query / impact (provenance via subclassing)
# ---------------------------------------------------------------------------


class ModelAuthorityTraversal(SuccessorTraversal):
    """Successor traversal + the EvidenceContract discriminator.

    Retired names (owner decision D4) are refused before traversal: the
    contract raises ``RetiredIdentityError`` ("retired; use <successor>") for
    them and the successor traversal records them as ``retired``.
    """

    def blocked_predicates(self) -> frozenset[str]:
        return frozenset(super().blocked_predicates()) - set(DISCRIMINATED_PREDICATES)

    def traverse(self, predicate, source, elements):
        disposition = (self.contract.refused or {}).get(predicate)
        if disposition is not None:
            self.unavailable(predicate, disposition, "retired")
            return []
        return super().traverse(predicate, source, elements)

    def evidence_contract_definitions(self, elements):
        """Live specializing definitions of the validated EvidenceContract root.

        Returns ``(root_id, definitions, closure, resolver)``. Root identity
        comes from the ingestion-validated kernel binding; the closure follows
        AUTHORED subsumption only and must contain exactly the expected number
        of specializing requirement definitions (ids, never names). Built once
        per corpus; a refusal is re-raised on every call.
        """
        return self.revision_index(elements).memo_bound(
            "evidence-contract-definitions",
            (self.kernel_bindings,),
            lambda: self._evidence_contract_definitions(elements),
        )

    def _evidence_contract_definitions(self, elements):
        from .relationships import build_relationship_graph

        by_id = {}
        for item in elements:
            identifier = item.get("@id") if isinstance(item, dict) else None
            if isinstance(identifier, str):
                by_id[identifier] = item
        graph = build_relationship_graph(list(by_id.values()))
        try:
            resolver = self._lineage_resolver(EVIDENCE_CONTRACT_CLASS, by_id, graph)
        except IdentityNotFoundError as exc:
            raise IdentityNotFoundError(f"{MODEL_EVIDENCE_CONTRACT_BLOCKED_REASON} ({exc})") from exc
        root_id = resolver["root_id"]
        closure = set(resolver["explicit_lineage_ids"])
        definitions = {i for i in closure - {root_id}
                       if str(by_id.get(i, {}).get("@type")) == "RequirementDefinition"}
        if len(definitions) != EXPECTED_EVIDENCE_CONTRACT_DEFINITIONS:
            raise IdentityNotFoundError(
                f"{MODEL_EVIDENCE_CONTRACT_BLOCKED_REASON} (found {len(definitions)} "
                "specializing definitions)")
        return root_id, definitions, closure, resolver

    def _evidence_contract_identity_ids(self, elements):
        """Owner-adopted discriminator: members are the usages explicitly typed
        by the validated root or one of the closure definitions."""
        root_id, definitions, closure, resolver = self.evidence_contract_definitions(elements)
        types = definitions | {root_id}

        def members():
            return {element for element, typed in resolver["typed_by"].items()
                    if element not in closure and set(typed) & types}

        return set(self.revision_index(elements).memo_bound(
            "evidence-contract-identity-ids",
            (self.kernel_bindings,),
            lambda: frozenset(members())))


def _component_provenance(contract) -> list[dict[str, str]]:
    components = contract._components
    entries = [{"authority": "semantic-authority",
                "source": f"semantic-authority://{components['semantic_authority']['id']}"}]
    for record in components["layers"]:
        if record.get("frozen"):
            entries.append({"authority": "semantic-authority",
                            "source": f"projection-layer://{record['layer']} (frozen)",
                            "sha256": _canonical_digest([item["sha256"] for item in record["chain"]])})
        else:
            entries.append({"authority": "semantic-authority",
                            "source": f"projection-layer://{record['layer']}",
                            "sha256": record["projection"]["sha256"]})
    entries.append({"authority": "semantic-authority",
                    "source": f"successor-contract://{components['successor_contract']['id']}"})
    return entries


class ModelAuthorityQueryService(SuccessorQueryService):
    def _provenance(self):
        return super()._provenance() + _component_provenance(self.contract)

    def _semantic_authority(self):
        return {"id": self.semantic_authority_id, "kind": MODEL_AUTHORITY,
                "semantic_authority": self.contract.identity.id,
                "refused_count": len(self.contract.refused),
                "note": ("model-built semantic authority; every identity resolves through "
                         "its verified model layer; retired and refused identities answer "
                         "only with their disposition")}

    def model_status(self):
        report = super().model_status()
        report["semantic_authority"] = {**self._semantic_authority(),
                                        "provenance": self.contract.provenance()}
        return report


def model_provenance(binding: Any, derived_source: str) -> list[dict[str, str]]:
    """Revision, model and semantic-authority provenance of one answer."""
    return [
        {"authority": "authoritative", "source": f"git://{binding.git_repository}/{binding.git_commit}"},
        {"authority": "authoritative", "source": f"sysml://{binding.sysml_project_id}/{binding.sysml_commit_id}"},
        {"authority": "semantic-authority",
         "source": f"semantic-authority://{binding.semantic_authority.id}"},
        {"authority": "derived", "source": derived_source},
    ]


class ModelAuthorityImpactService(ImpactService):
    semantic_authority_id: str = ""

    def impact(self, identifier, *, git_revision):
        report = super().impact(identifier, git_revision=git_revision)
        report["provenance"] = model_provenance(
            self.binding, "de4sdv.semantic.impact"
        ) + _component_provenance(self.contract)
        report["semantic_authority"] = self.contract.provenance()
        return report


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def model_facade(root: Path = ROOT, *, contract: KernelContract | None = None) -> ModelAuthorityFacade:
    """The facade over the checkout's model-built contract.

    No binding is consulted. Production construction goes through
    :func:`de4sdv.semantic.deployment_runtime.build_deployment_runtime`, which
    runs the startup check first and passes the contract it verified.
    """
    root = Path(root)
    records, provisions = load_model_layers(root)
    successor = generate_model_successor_contract(root, records=records, provisions=provisions)
    routing = _model_routing(root, records, provisions, successor)
    if contract is None:
        contract = build_model_contract(root)
    components = {"layers": records, "semantic_authority": contract.identity.to_dict(),
                  "successor_contract": _successor_record(successor), "routing": routing.record()}
    return ModelAuthorityFacade(contract=contract, routing=routing, successor_contract=successor,
                                components=components)


def assemble_model_services(facade: ModelAuthorityFacade, binding: Any, model_repository: Any, *,
                            expected_git_revision: str,
                            service_class: type = ModelAuthorityQueryService) -> ModelAuthorityQueryService:
    """Assemble the live query/impact services over one facade and binding."""
    from .api_binding import OntologyApiBinder
    from .relationship_successor import route_successor_bindings

    index, routes = route_successor_bindings(facade.profile, binding)
    # Profile routing consumes ingestion-validated file/declaration/UUID tuples:
    # two successor profile pins can never share (or lack) one element identity.
    profile_pins = {**facade.profile["classes"], **facade.profile["carriers"]}
    selected = [b.element_id for b in index.bindings if b.ontology_class in profile_pins]
    if any(not i or not i.strip() for i in selected) or len(selected) != len(set(selected)):
        raise ValueError("overlapping or blank successor kernel identities")
    facade.binding_routes = routes
    binder = OntologyApiBinder(facade, model_repository, project_id=binding.sysml_project_id,
                               commit_id=binding.sysml_commit_id, kernel_bindings=index)
    traversal = ModelAuthorityTraversal(facade, kernel_bindings=index)
    impact = ModelAuthorityImpactService(repository=model_repository, binding=binding, contract=facade,
                                         binder=binder, traversal=traversal)
    impact.semantic_authority_id = facade.authority_id
    return service_class(
        repository=model_repository, binding=binding, contract=facade, binder=binder,
        traversal=traversal, impact_service=impact, expected_git_revision=expected_git_revision,
        semantic_authority_id=facade.authority_id)
