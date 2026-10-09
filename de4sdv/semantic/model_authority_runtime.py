"""O4 model-authority runtime (Wave C2): one closed ``mab-`` bundle, one authority.

The model-authority bundle (``de4sdv.model-authority-bundle/v2``) is a
deployment input. It binds, under one content digest:

- every layer of the model-built kernel contract
  (:mod:`de4sdv.semantic.model_contract`): the live projection/profile pairs
  (definitions batch 1 and 2, O2+ native/library rows, vocabulary carriers)
  and the frozen O2-chain records (path, schema, sha256, ``frozen: true``);
- the semantic-authority identity of that contract (``sai-`` id), which the
  revision binding must carry;
- the relationship-successor contract generated from the model at bundle
  construction and regenerated and compared again at runtime construction;
- the executed implementation manifest (every runtime source this path runs);
- the routing table: exactly one provider per identity and an EMPTY residual
  (construction refuses any identity without a model provider).

There is no authored ontology, no O3 component and no other authority:
retired and refused identities answer only with their disposition.

After closure the bundle carries a structured attestation (binding,
validation evidence, recomputed activation eligibility). The attestation,
not the id, carries the deployment binding, so re-closing at a deployment
binding reproduces the privileged ``mab-`` id.

Selection is explicit (``DE4SDV_SEMANTIC_AUTHORITY=model`` with
``DE4SDV_MODEL_AUTHORITY_BUNDLE`` and ``DE4SDV_MODEL_AUTHORITY_BUNDLE_ID``),
routed by :func:`de4sdv.semantic.composition_construction.build_explicit_semantic_runtime`.
Every failure refuses; nothing falls back.

``hasRelevantEvidenceContract`` uses the owner-adopted discriminator: its
range is the authored type closure of the validated ``EvidenceContract``
kernel root, which must contain exactly :data:`EXPECTED_EVIDENCE_CONTRACT_DEFINITIONS`
specializing definitions (the eight AEBS evidence contracts). For a closed
bundle the live closure must also equal, by API element id, the bound
eight-member closure of ``definition-batch2-projection.json`` as validated by
the ingestion binding rule (API type, declared name and serializer source
file). Any other population fails closed with
:data:`MODEL_EVIDENCE_CONTRACT_BLOCKED_REASON`.

Non-claims: constructing or closing a bundle is not production activation,
compliance or a semantic proof beyond the bound artifacts. Production
activation stays owner-gated.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import sys
from dataclasses import dataclass, replace
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
    bound_evidence_contract_closure,
    build_model_contract,
    canonical_json,
    compute_routing,
    generate_model_successor_contract,
    load_model_layers,
    load_register_rows,
    validate_closure_members,
)
from .relationship_successor import SuccessorQueryService, SuccessorTraversal

ROOT = Path(__file__).resolve().parents[2]

MODEL_AUTHORITY = "model"
AUTHORITY_ENV = "DE4SDV_SEMANTIC_AUTHORITY"
MODEL_BUNDLE_PATH_ENV = "DE4SDV_MODEL_AUTHORITY_BUNDLE"
MODEL_BUNDLE_ID_ENV = "DE4SDV_MODEL_AUTHORITY_BUNDLE_ID"

MODEL_BUNDLE_SCHEMA = "de4sdv.model-authority-bundle/v2"
MODEL_ATTESTATION_SCHEMA = "de4sdv.model-authority-closure/v2"
IMPLEMENTATION_SCHEMA = "de4sdv.model-authority-implementation/v2"
BUNDLE_ID_RE = re.compile(r"^mab-[0-9a-f]{32}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")

#: Activation-gating validation evidence (each exactly ``passed`` + digest).
#: The three batteries run under this candidate bundle at the same revision;
#: the requirement-population delta is measured evidence, not a gate.
REQUIRED_MODEL_VALIDATIONS = (
    "model_projection_coverage",
    "model_runtime_answers",
    "verification_anchor_readback",
    "full_model_semantic_queries",
    "product_line_scope",
    "semantic_mcp",
)

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
    """Every layer of the model-built contract: (bundle records, provisions)."""
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


# ---------------------------------------------------------------------------
# Implementation manifest
# ---------------------------------------------------------------------------

#: Every runtime source the model-authority path executes.
IMPLEMENTATION_FILES = (
    "de4sdv/semantic/model_authority_runtime.py",
    "de4sdv/semantic/model_contract.py",
    "de4sdv/semantic/kernel_contract.py",
    "de4sdv/semantic/composition_construction.py",
    "de4sdv/semantic/authority_selection.py",
    "de4sdv/semantic/relationship_successor.py",
    "de4sdv/semantic/relationship_successor_contract.py",
    "de4sdv/semantic/definition_candidate.py",
    "de4sdv/semantic/definition_candidate_provider.py",
    "de4sdv/semantic/definition_migration.py",
    "de4sdv/semantic/model_edges.py",
    "de4sdv/semantic/relationships.py",
    "de4sdv/semantic/traversal.py",
    "de4sdv/semantic/query.py",
    "de4sdv/semantic/impact.py",
    "de4sdv/semantic/api_binding.py",
    "de4sdv/semantic/kernel_binding_index.py",
    "de4sdv/semantic/validation.py",
    "de4sdv/sysml_api/client.py",
    "de4sdv/sysml_api/repository.py",
    "de4sdv/sysml_api/revisions.py",
)


def _executed_sources() -> dict[str, str | None]:
    from de4sdv.sysml_api import client, repository, revisions
    from . import (api_binding, authority_selection, composition_construction,
                   definition_candidate, definition_candidate_provider, definition_migration,
                   impact, kernel_binding_index, kernel_contract, model_contract, model_edges,
                   query, relationship_successor, relationship_successor_contract,
                   relationships, traversal, validation)

    modules = (sys.modules[__name__], model_contract, kernel_contract, composition_construction,
               authority_selection, relationship_successor, relationship_successor_contract,
               definition_candidate, definition_candidate_provider, definition_migration,
               model_edges, relationships, traversal, query, impact, api_binding,
               kernel_binding_index, validation, client, repository, revisions)
    return {rel: inspect.getsourcefile(module) for rel, module in zip(IMPLEMENTATION_FILES, modules)}


def implementation_manifest(root: Path = ROOT) -> dict[str, Any]:
    """Bind executed runtime bytes; refuse substituted (external) sources."""
    files = {}
    sources = _executed_sources()
    for relative in IMPLEMENTATION_FILES:
        expected = Path(root) / relative
        actual = sources[relative]
        if actual is None or Path(actual).resolve() != expected.resolve():
            raise ModelAuthorityRefused(f"unexpected implementation source for {relative}")
        files[relative] = _sha256_bytes(expected.read_bytes())
    return {"schema": IMPLEMENTATION_SCHEMA, "files": files,
            "id": "mai-" + hashlib.sha256(canonical_json(files).encode()).hexdigest()[:32]}


# ---------------------------------------------------------------------------
# Bundle construction / closure / verification
# ---------------------------------------------------------------------------

_ID_COMPONENTS = ("schema", "git_revision", "components")
_COMPONENT_KEYS = ("layers", "semantic_authority", "successor_contract", "routing",
                   "implementation_manifest")


def compute_model_bundle_id(bundle: Mapping[str, Any]) -> str:
    payload = {key: bundle.get(key) for key in _ID_COMPONENTS}
    return "mab-" + hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()[:32]


def model_authority_id(bundle_id: str) -> str:
    """Service authority id (provenance, cache/snapshot identity)."""
    return f"mab:{bundle_id}"


def _successor_record(contract: Mapping[str, Any]) -> dict[str, Any]:
    return {"id": contract["id"], "schema": contract["schema"],
            "sha256": _canonical_digest(contract),
            "relations": sorted(_successor_names(contract)),
            "retired": sorted(contract.get("retired") or ())}


def model_components(root: Path = ROOT) -> dict[str, Any]:
    """Everything the bundle id binds, recomputed from the checkout."""
    root = Path(root)
    records, provisions = load_model_layers(root)
    successor = generate_model_successor_contract(root, records=records, provisions=provisions)
    routing = _model_routing(root, records, provisions, successor)
    contract = build_model_contract(root)
    return {
        "layers": records,
        "semantic_authority": contract.identity.to_dict(),
        "successor_contract": _successor_record(successor),
        "routing": routing.record(),
        "implementation_manifest": implementation_manifest(root),
    }


def _component_problems(components: Mapping[str, Any]) -> list[str]:
    routing = components.get("routing") or {}
    problems = []
    if routing.get("duplicates"):
        problems.append("duplicate providers: " + "; ".join(routing["duplicates"]))
    if routing.get("residual"):
        problems.append("routing residual is not empty: " + ", ".join(sorted(routing["residual"])))
    return problems


def build_model_bundle(root: Path = ROOT, *, git_revision: str) -> dict[str, Any]:
    """Construct a candidate (unclosed) model-authority bundle."""
    if not _REVISION_RE.fullmatch(str(git_revision or "")):
        raise ModelAuthorityRefused("git_revision must be a full 40-hex commit id")
    components = model_components(root)
    problems = _component_problems(components)
    if problems:
        raise ModelAuthorityRefused("; ".join(problems))
    bundle = {
        "schema": MODEL_BUNDLE_SCHEMA,
        "git_revision": git_revision,
        "components": components,
        "state": "candidate",
        "claim_boundary": ("deployment input; closure is not activation, compliance "
                           "or certification"),
    }
    bundle["bundle_id"] = compute_model_bundle_id(bundle)
    return bundle


def _eligibility(attestation: Mapping[str, Any]) -> bool:
    validation = attestation.get("validation")
    return (attestation.get("definition_closure_closed") is True
            and isinstance(validation, Mapping)
            and set(validation) == set(REQUIRED_MODEL_VALIDATIONS)
            and all(isinstance(r, Mapping) and r.get("status") == "passed"
                    and _DIGEST_RE.fullmatch(str(r.get("sha256") or ""))
                    for r in validation.values()))


def build_model_closure_attestation(bundle: Mapping[str, Any], *, binding: Any,
                                    binding_sha256: str, definition_closure_closed: bool,
                                    validations: Mapping[str, Mapping[str, Any]],
                                    generated_at: str,
                                    evidence_contract_closure: list[Mapping[str, str]] | None = None,
                                    ) -> dict[str, Any]:
    attestation = {
        "schema": MODEL_ATTESTATION_SCHEMA,
        "bundle_id": bundle["bundle_id"],
        "git_revision": bundle["git_revision"],
        "binding_sha256": binding_sha256,
        "sysml_project_id": str(binding.sysml_project_id),
        "sysml_commit_id": str(binding.sysml_commit_id),
        "semantic_authority_id": str(binding.semantic_authority.id),
        "definition_closure_closed": bool(definition_closure_closed),
        "evidence_contract_closure": sorted(
            (dict(m) for m in evidence_contract_closure or ()),
            key=lambda m: (str(m.get("source_file")), str(m.get("declaration")))),
        "validation": {name: dict(record) for name, record in validations.items()},
        "generated_at": generated_at,
    }
    attestation["activation_eligible"] = _eligibility(attestation)
    return attestation


def close_model_bundle(bundle: Mapping[str, Any], attestation: Mapping[str, Any]) -> dict[str, Any]:
    if attestation.get("schema") != MODEL_ATTESTATION_SCHEMA:
        raise ModelAuthorityRefused("model closure attestation schema mismatch")
    if attestation.get("bundle_id") != bundle.get("bundle_id"):
        raise ModelAuthorityRefused("closure attestation is bound to a different bundle id")
    closed = json.loads(json.dumps(dict(bundle)))
    closed["state"] = "closed"
    closed["closure"] = json.loads(json.dumps(dict(attestation)))
    return closed


def verify_model_bundle(bundle: Mapping[str, Any], *, root: Path = ROOT, binding: Any = None,
                        binding_sha256: str | None = None, require_closed: bool = False,
                        validation_artifacts: Mapping[str, Path] | None = None) -> list[str]:
    """Recompute every bound component from the checkout; errors (empty = valid)."""
    if not isinstance(bundle, Mapping) or bundle.get("schema") != MODEL_BUNDLE_SCHEMA:
        return [f"model bundle schema mismatch: expected {MODEL_BUNDLE_SCHEMA}"]
    errors: list[str] = []
    allowed = set(_ID_COMPONENTS) | {"bundle_id", "state", "closure", "claim_boundary"}
    extra = sorted(set(bundle) - allowed)
    if extra:
        errors.append(f"model bundle carries unknown keys: {extra}")
    bundle_id = str(bundle.get("bundle_id") or "")
    if not BUNDLE_ID_RE.fullmatch(bundle_id):
        errors.append("model bundle id is not an exact mab-<32 hex> token")
    if bundle_id != compute_model_bundle_id(bundle):
        errors.append("model bundle id does not match the recomputed content digest")
    state = bundle.get("state")
    if state not in ("candidate", "closed"):
        errors.append(f"model bundle state must be candidate|closed, got {state!r}")
    components = bundle.get("components")
    if not isinstance(components, Mapping):
        return errors + ["model bundle has no components"]
    try:
        expected = model_components(root)
    except Exception as exc:  # recomputation failures are verification failures
        return errors + [f"model components cannot be recomputed: {exc}"]
    for key in _COMPONENT_KEYS:
        if components.get(key) != expected[key]:
            errors.append(f"model bundle component {key!r} differs from the checkout")
    if set(components) != set(expected):
        errors.append("model bundle component set differs")
    errors.extend(_component_problems(expected))
    if require_closed and state != "closed":
        errors.append("model bundle is not closed: production selection requires the closure attestation")
    if state == "closed":
        closure = bundle.get("closure")
        if not isinstance(closure, Mapping):
            errors.append("closed model bundle carries no closure attestation")
        else:
            errors.extend(_closure_errors(bundle, closure, root=root, binding=binding,
                                          binding_sha256=binding_sha256,
                                          validation_artifacts=validation_artifacts))
    return errors


def _closure_member_errors(closure, root) -> list[str]:
    members = closure.get("evidence_contract_closure")
    try:
        bound = {(m["source_file"], m["declaration"]) for m in bound_evidence_contract_closure(root)}
    except ModelAuthorityRefused as exc:
        return [str(exc)]
    if not isinstance(members, list) or not all(isinstance(m, Mapping) for m in members):
        return ["closure attests no EvidenceContract closure members"]
    ids = [m.get("element_id") for m in members]
    if ({(m.get("source_file"), m.get("declaration")) for m in members} != bound
            or len(members) != len(bound) or len(set(ids)) != len(ids)
            or not all(isinstance(i, str) and i and i == i.strip() for i in ids)):
        return ["closure evidence_contract_closure does not attest exactly the bound "
                "EvidenceContract closure members, each with one distinct validated element id"]
    return []


def _closure_errors(bundle, closure, *, root, binding, binding_sha256, validation_artifacts):
    errors = _closure_member_errors(closure, root)
    if closure.get("schema") != MODEL_ATTESTATION_SCHEMA:
        errors.append("model closure attestation schema mismatch")
    if closure.get("bundle_id") != bundle.get("bundle_id"):
        errors.append("closure attestation is bound to a different bundle id")
    if closure.get("git_revision") != bundle.get("git_revision"):
        errors.append("closure attestation git revision mismatch")
    if closure.get("activation_eligible") is not _eligibility(closure):
        errors.append("recorded activation_eligible differs from the recomputed value")
    authority = ((bundle.get("components") or {}).get("semantic_authority") or {}).get("id")
    if closure.get("semantic_authority_id") != authority:
        errors.append("closure semantic_authority_id differs from the bundle's semantic authority")
    for name, record in (closure.get("validation") or {}).items():
        if not isinstance(record, Mapping) or not _DIGEST_RE.fullmatch(str(record.get("sha256") or "")):
            errors.append(f"validation {name!r} carries no exact sha256 digest")
            continue
        if validation_artifacts and name in validation_artifacts:
            actual = _sha256_bytes(Path(validation_artifacts[name]).read_bytes())
            if actual != record["sha256"]:
                errors.append(f"validation {name!r} digest differs from the produced output")
    if binding is not None:
        if closure.get("binding_sha256") != binding_sha256:
            errors.append("closure binding digest differs from the selected binding")
        if (closure.get("sysml_project_id") != str(binding.sysml_project_id)
                or closure.get("sysml_commit_id") != str(binding.sysml_commit_id)):
            errors.append("closure SysML project/commit differs from the binding")
        if binding.git_commit != bundle.get("git_revision"):
            errors.append("binding git_commit differs from the bundle revision")
        if binding.semantic_authority.to_dict() != (bundle.get("components") or {}).get(
                "semantic_authority"):
            errors.append("binding semantic authority differs from the bundle's semantic authority")
    return errors


# ---------------------------------------------------------------------------
# Runtime facade (duck-compatible with KernelContract)
# ---------------------------------------------------------------------------


class ModelAuthorityFacade:
    """The model-built contract plus bundle identity and the successor profile."""

    def __init__(self, *, contract: KernelContract, routing: Routing,
                 successor_contract: Mapping[str, Any], bundle_id: str,
                 components: Mapping[str, Any]) -> None:
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
        self.bundle_id = bundle_id
        self.authority_id = model_authority_id(bundle_id)
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
            "bundle_id": self.bundle_id,
            "semantic_authority_id": self.identity.id,
            "layers": layers,
            "successor_contract_id": self._components["successor_contract"]["id"],
            "implementation_manifest_id": self._components["implementation_manifest"]["id"],
            "refused_identities": sorted(self.refused),
            "binding_routes": list(self.binding_routes),
            "status": "model authority; production activation is owner-gated",
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

    def __init__(self, contract, kernel_bindings, closure_member_ids=None):
        super().__init__(contract, kernel_bindings)
        #: Attested element ids of the bound EvidenceContract closure (closed
        #: bundles); ``None`` for a candidate, which only the evidence steps
        #: and tests serve and whose compare step checks member identity itself.
        self.closure_member_ids = (None if closure_member_ids is None
                                   else frozenset(closure_member_ids))

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
        AUTHORED subsumption only. It must contain exactly the expected number
        of specializing requirement definitions and, when attested, exactly
        the bound members' validated element ids (ids, never names). Built
        once per corpus; a refusal is re-raised on every call.
        """
        return self.revision_index(elements).memo_bound(
            "evidence-contract-definitions",
            (self.kernel_bindings, self.closure_member_ids),
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
        if self.closure_member_ids is not None and definitions != self.closure_member_ids:
            raise IdentityNotFoundError(
                f"{MODEL_EVIDENCE_CONTRACT_BLOCKED_REASON} (live closure differs from the "
                f"attested bound members: {len(definitions - self.closure_member_ids)} "
                "unbound, "
                f"{len(self.closure_member_ids - definitions)} missing)")
        return root_id, definitions, closure, resolver

    def _evidence_contract_identity_ids(self, elements):
        """Owner-adopted discriminator: members are the usages explicitly typed
        by the validated root or one of the bound closure definitions."""
        root_id, definitions, closure, resolver = self.evidence_contract_definitions(elements)
        types = definitions | {root_id}

        def members():
            return {element for element, typed in resolver["typed_by"].items()
                    if element not in closure and set(typed) & types}

        return set(self.revision_index(elements).memo_bound(
            "evidence-contract-identity-ids",
            (self.kernel_bindings, self.closure_member_ids),
            lambda: frozenset(members())))


def _component_provenance(contract) -> list[dict[str, str]]:
    components = contract._components
    entries = [{"authority": "semantic-authority", "source": f"model-authority://{contract.authority_id}"},
               {"authority": "semantic-authority",
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
    entries.append({"authority": "runtime-implementation",
                    "source": f"implementation://{components['implementation_manifest']['id']}"})
    return entries


class ModelAuthorityQueryService(SuccessorQueryService):
    def _provenance(self):
        return super()._provenance() + _component_provenance(self.contract)

    def _semantic_authority(self):
        return {"id": self.semantic_authority_id, "kind": MODEL_AUTHORITY,
                "bundle_id": self.contract.bundle_id,
                "semantic_authority": self.contract.identity.id,
                "refused_count": len(self.contract.refused),
                "note": ("explicitly selected model-authority bundle; every identity "
                         "resolves through its verified model layer; retired and refused "
                         "identities answer only with their disposition")}

    #: Set by :func:`build_model_authority_runtime` to the verified selection.
    selection: "ModelAuthoritySelection | None" = None

    def authority_status(self) -> dict[str, Any]:
        """Entry-point identity contract (``authority``/``bundle_id``/
        ``source_revision``/``refused``/``rollback``)."""
        document = self.selection.bundle_document if self.selection is not None else {}
        return {"authority": MODEL_AUTHORITY, "bundle_id": self.contract.bundle_id,
                "authority_id": self.semantic_authority_id,
                "source_revision": str(document.get("git_revision") or ""),
                "semantic_authority": self.contract.identity.id,
                "refused": sorted(self.contract.refused),
                "rollback": "redeploy the pre-Wave-C production revision",
                "activation_blocked": (True if self.selection is None
                                       else self.selection.activation_blocked)}

    def model_status(self):
        report = super().model_status()
        report["semantic_authority"] = {**self._semantic_authority(),
                                        "provenance": self.contract.provenance()}
        return report


def model_provenance(binding: Any, authority_id: str, derived_source: str) -> list[dict[str, str]]:
    """Revision, model and semantic-authority provenance of one answer."""
    return [
        {"authority": "authoritative", "source": f"git://{binding.git_repository}/{binding.git_commit}"},
        {"authority": "authoritative", "source": f"sysml://{binding.sysml_project_id}/{binding.sysml_commit_id}"},
        {"authority": "semantic-authority", "source": f"model-authority://{authority_id}"},
        {"authority": "semantic-authority",
         "source": f"semantic-authority://{binding.semantic_authority.id}"},
        {"authority": "derived", "source": derived_source},
    ]


class ModelAuthorityImpactService(ImpactService):
    semantic_authority_id: str = ""

    def impact(self, identifier, *, git_revision):
        report = super().impact(identifier, git_revision=git_revision)
        report["provenance"] = model_provenance(
            self.binding, self.semantic_authority_id, "de4sdv.semantic.impact"
        ) + _component_provenance(self.contract)
        report["semantic_authority"] = self.contract.provenance()
        return report


# ---------------------------------------------------------------------------
# Selection + construction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelAuthoritySelection:
    bundle_id: str
    bundle_path: Path
    bundle_document: Mapping[str, Any]
    kind: str = MODEL_AUTHORITY
    activation_blocked: bool = True

    def provenance(self) -> dict[str, Any]:
        components = self.bundle_document.get("components") or {}
        return {"kind": MODEL_AUTHORITY, "authority_id": model_authority_id(self.bundle_id),
                "bundle_id": self.bundle_id, "bundle_path": str(self.bundle_path),
                "git_revision": str(self.bundle_document.get("git_revision") or ""),
                "semantic_authority": str((components.get("semantic_authority") or {}).get("id") or ""),
                "activation_blocked": self.activation_blocked}


def resolve_model_selection(*, bundle_path: "str | Path | None" = None, bundle_id: str | None = None,
                            environ: Mapping[str, str] | None = None) -> ModelAuthoritySelection:
    env = os.environ if environ is None else environ
    path_value = bundle_path if bundle_path is not None else env.get(MODEL_BUNDLE_PATH_ENV, "")
    id_value = bundle_id if bundle_id is not None else env.get(MODEL_BUNDLE_ID_ENV, "")
    if not str(path_value or "").strip():
        raise ModelAuthorityRefused(f"{AUTHORITY_ENV}=model requires {MODEL_BUNDLE_PATH_ENV}")
    if not isinstance(id_value, str) or not BUNDLE_ID_RE.fullmatch(id_value):
        raise ModelAuthorityRefused(
            f"{AUTHORITY_ENV}=model requires {MODEL_BUNDLE_ID_ENV} as an exact mab-<32 hex> token")
    path = Path(str(path_value))
    if not path.is_file():
        raise ModelAuthorityRefused(f"model authority bundle not found: {path} (no fallback)")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ModelAuthorityRefused(f"model authority bundle is not readable JSON: {path}: {exc}") from exc
    if not isinstance(document, dict) or document.get("schema") != MODEL_BUNDLE_SCHEMA:
        raise ModelAuthorityRefused(f"model authority bundle schema mismatch: {path} "
                                    f"(expected {MODEL_BUNDLE_SCHEMA})")
    if document.get("bundle_id") != id_value:
        raise ModelAuthorityRefused("requested model bundle id does not equal the document id")
    return ModelAuthoritySelection(bundle_id=id_value, bundle_path=path, bundle_document=document)


@dataclass(frozen=True)
class ModelAuthority:
    facade: ModelAuthorityFacade
    bundle_id: str
    authority_id: str
    activation_eligible: bool
    definitions: Any
    closure_member_ids: frozenset[str] | None = None


def load_model_authority(document: Mapping[str, Any], *, root: Path = ROOT, binding: Any,
                         binding_sha256: str, expected_git_revision: str,
                         require_activation_eligible: bool = False,
                         validation_artifacts: Mapping[str, Path] | None = None) -> ModelAuthority:
    from .definition_migration import load_definition_migration_authority

    root = Path(root)
    errors = verify_model_bundle(document, root=root, binding=binding, binding_sha256=binding_sha256,
                                 require_closed=require_activation_eligible,
                                 validation_artifacts=validation_artifacts)
    if binding.git_commit != expected_git_revision or document.get("git_revision") != expected_git_revision:
        errors.append("model bundle/binding revision differs from the expected runtime revision")
    if errors:
        raise ModelAuthorityRefused("; ".join(errors))
    closure = document.get("closure") or {}
    eligible = document.get("state") == "closed" and closure.get("activation_eligible") is True
    if require_activation_eligible and not eligible:
        raise ModelAuthorityRefused("production activation requires a closed, activation-eligible model bundle")
    components = document["components"]
    contract = build_model_contract(root)
    if contract.identity.to_dict() != components["semantic_authority"]:
        raise ModelAuthorityRefused("model-built contract identity differs from the bundle")
    binding.require_semantic_authority(contract.identity)
    definitions = load_definition_migration_authority(
        root, binding=binding, require_activation_eligible=True,
        expected_git_revision=expected_git_revision)
    records, provisions = load_model_layers(root)
    successor = generate_model_successor_contract(root, records=records, provisions=provisions)
    if _successor_record(successor) != components["successor_contract"]:
        raise ModelAuthorityRefused("successor contract regenerated from the model differs from the bundle")
    routing = _model_routing(root, records, provisions, successor)
    if routing.record() != components["routing"]:
        raise ModelAuthorityRefused("routing recomputed at construction differs from the bundle")
    for name in definitions.identities:
        if routing.providers.get(name) is None or routing.providers[name].layer != "definition":
            raise ModelAuthorityRefused(f"verified definition {name!r} is not routed to the definition layer")
        if routing.providers[name].mapping != definitions.provider.mapping(name):
            raise ModelAuthorityRefused(f"definition layer mapping differs from the verified pair: {name}")
    facade = ModelAuthorityFacade(contract=contract, routing=routing, successor_contract=successor,
                                  bundle_id=document["bundle_id"], components=components)
    member_ids = None
    if document.get("state") == "closed":
        member_ids = frozenset(m["element_id"] for m in closure["evidence_contract_closure"])
    return ModelAuthority(facade=facade, bundle_id=document["bundle_id"],
                          authority_id=facade.authority_id, activation_eligible=eligible,
                          definitions=definitions, closure_member_ids=member_ids)


def model_facade(root: Path = ROOT, *, bundle_id: str = "mab-" + "0" * 32) -> ModelAuthorityFacade:
    """An UNVERIFIED facade over the checkout (no bundle, no closure, no binding).

    For tests and tooling that exercise the runtime over synthetic APIs.
    Production construction goes through :func:`build_model_authority_runtime`,
    which verifies the bundle, the binding and the definition closure first.
    """
    root = Path(root)
    records, provisions = load_model_layers(root)
    successor = generate_model_successor_contract(root, records=records, provisions=provisions)
    routing = _model_routing(root, records, provisions, successor)
    contract = build_model_contract(root)
    components = {"layers": records, "semantic_authority": contract.identity.to_dict(),
                  "successor_contract": _successor_record(successor), "routing": routing.record(),
                  "implementation_manifest": implementation_manifest(root)}
    return ModelAuthorityFacade(contract=contract, routing=routing, successor_contract=successor,
                                bundle_id=bundle_id, components=components)


def assemble_model_services(facade: ModelAuthorityFacade, binding: Any, model_repository: Any, *,
                            expected_git_revision: str, closure_member_ids=None) -> "ModelAuthorityQueryService":
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
    traversal = ModelAuthorityTraversal(facade, kernel_bindings=index,
                                        closure_member_ids=closure_member_ids)
    impact = ModelAuthorityImpactService(repository=model_repository, binding=binding, contract=facade,
                                         binder=binder, traversal=traversal)
    impact.semantic_authority_id = facade.authority_id
    return ModelAuthorityQueryService(
        repository=model_repository, binding=binding, contract=facade, binder=binder,
        traversal=traversal, impact_service=impact, expected_git_revision=expected_git_revision,
        semantic_authority_id=facade.authority_id)


def build_model_authority_runtime(repo_root: "str | Path" = ROOT,
                                  bundle_path: "str | Path | None" = None,
                                  expected_id: str | None = None, *,
                                  api_url: str, binding_path: Path, expected_git_revision: str,
                                  api_timeout: float = 600.0,
                                  environ: Mapping[str, str] | None = None,
                                  require_activation_eligible: bool = True,
                                  production: bool = False,
                                  validation_artifacts: Mapping[str, Path] | None = None):
    """Verify the model bundle once, then assemble the live services.

    ``bundle_path``/``expected_id`` default to ``DE4SDV_MODEL_AUTHORITY_BUNDLE``
    / ``DE4SDV_MODEL_AUTHORITY_BUNDLE_ID``; both are required and must match.
    Returns the query service (the runtime); its ``selection`` attribute holds
    the verified :class:`ModelAuthoritySelection` and ``authority_status()``
    reports the entry identity. Activation eligibility (a closed bundle whose
    recomputed closure is eligible) is required by default; only an explicit
    ``require_activation_eligible=False`` (the privileged evidence steps and
    tests) serves a candidate or ineligible bundle, and ``production=True``
    always requires it. Every failure raises :class:`ModelAuthorityRefused`.
    """
    root = Path(repo_root)
    from de4sdv.sysml_api import client, repository
    from de4sdv.sysml_api.revisions import RevisionBinding

    selection = resolve_model_selection(bundle_path=bundle_path, bundle_id=expected_id,
                                        environ=environ)
    raw_binding = Path(binding_path).read_bytes()
    try:
        binding = RevisionBinding.from_dict(json.loads(raw_binding))
    except ValueError as exc:
        raise ModelAuthorityRefused(f"revision binding refused: {exc}") from exc
    binding.require_current(expected_git_revision)
    authority = load_model_authority(
        selection.bundle_document, root=root, binding=binding,
        binding_sha256=_sha256_bytes(raw_binding), expected_git_revision=expected_git_revision,
        require_activation_eligible=require_activation_eligible or production,
        validation_artifacts=validation_artifacts)
    model_repository = repository.SysMLRepository(client.ApiClient(api_url, timeout=api_timeout))
    service = assemble_model_services(
        authority.facade, binding, model_repository, expected_git_revision=expected_git_revision,
        closure_member_ids=authority.closure_member_ids)
    service.selection = replace(selection, activation_blocked=not authority.activation_eligible)
    return service
