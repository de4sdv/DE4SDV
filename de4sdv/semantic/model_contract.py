"""The model-built kernel contract (O4 Wave C2, design E1).

Builds the :class:`~de4sdv.semantic.kernel_contract.KernelContract` the
runtime, ingestion, validators and gates consume from model-generated sources
only:

- the live projection layers (definition batch 1 and batch 2, O2+ native and
  library rows, vocabulary carriers);
- the frozen O2-chain layer: the O2 v1-v1.2 Semantic Projection / API
  Representation Profile records (frozen O2 records, owner decision Q7) for
  the 13 identities the O3 cutover migrated. They are read-only data; their
  bytes are pinned by ``de4sdv/semantic/contract-data/frozen-records.json``;
- the relationship-successor contract generated from the model
  (``de4sdv_trace_vocabulary.sysml``), with class pins taken from the
  layers above (:func:`model_class_pins`);
- the kernel-internal declarations manifest (owner decision D3) for the
  gate's ``exclusions``.

Routing gives every identity exactly one provider (duplicates refused).
Registered non-retained rows and successor retirements have no provider:
they are *refused* with their disposition, never served. No authored
ontology file exists or is read.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from de4sdv.sysml_api.revisions import SEMANTIC_AUTHORITY_SCHEMA, SemanticAuthorityIdentity

from .kernel_contract import (
    KernelContract,
    KernelExternalMapping,
    KernelFileMapping,
    KernelNativeMapping,
    RelationshipMapping,
    declaration_identity,
)

ROOT = Path(__file__).resolve().parents[2]

ROUTING_SCHEMA = "de4sdv.model-authority-routing/v2"

#: Owner decision 5 (2026-10-07): the EvidenceContract type closure is exactly
#: the eight AEBS evidence-contract definitions.
EXPECTED_EVIDENCE_CONTRACT_DEFINITIONS = 8
EVIDENCE_CONTRACT_CLASS = "EvidenceContract"
DISCRIMINATED_PREDICATES = ("hasRelevantEvidenceContract",)


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


#: The frozen O2 chain (dependency order). Frozen O2 records; read-only data.
O2_CHAIN_LAYER = "o2-chain"
O2_PROJECTION_CHAIN = (
    ("de4sdv/semantic/contract-data/frozen-records/semantic-projection-v1.json", "de4sdv.semantic-projection.v1"),
    ("de4sdv/semantic/contract-data/frozen-records/semantic-projection-v1.1.json", "de4sdv.semantic-projection.v1.1"),
    ("de4sdv/semantic/contract-data/frozen-records/semantic-projection-v1.2.json", "de4sdv.semantic-projection.v1.2"),
)
O2_PROFILE_CHAIN = (
    ("de4sdv/semantic/contract-data/frozen-records/api-representation-profile-v1.json", "de4sdv.api-representation-profile.v1"),
    ("de4sdv/semantic/contract-data/frozen-records/api-representation-profile-v1.1.json", "de4sdv.api-representation-profile.v1.1"),
    ("de4sdv/semantic/contract-data/frozen-records/api-representation-profile-v1.2.json", "de4sdv.api-representation-profile.v1.2"),
)
#: The identities the O3 cutover migrated, served from the frozen O2 chain.
O2_CHAIN_CLASSES = (
    "MethodPhase",
    "MethodContractObligation",
    "EvaluationScopeMembership",
    "EvaluationSourceKind",
    "TestedScopeDeclaration",
    "RetainedExecutionRecordReference",
    "AcceptanceAttestationReference",
    "VerificationCase",
)
O2_CHAIN_RELATIONSHIPS = (
    "hasSubject",
    "verifiedBy",
    "derivesRequirementFromNeed",
    "derivedRequirementsOfNeed",
    "hasRelevantArchitecture",
)
O2_CHAIN_IDENTITIES = O2_CHAIN_CLASSES + O2_CHAIN_RELATIONSHIPS

KERNEL_INTERNAL_PATH = "de4sdv/semantic/contract-data/kernel-internal-declarations.yaml"
CONTRACT_SOURCE = "model-authority://projection-layers"





class ModelAuthorityRefused(ValueError):
    """The model-built contract cannot be built from this checkout (fail closed)."""



# ---------------------------------------------------------------------------
# Projection layers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LayerSpec:
    name: str
    projection_path: str
    projection_schema: str
    profile_path: str
    profile_schema: str
    required: bool = True


#: Precedence order. A later layer may never re-provide an identity.
LAYERS: tuple[LayerSpec, ...] = (
    LayerSpec("definition",
              "de4sdv/semantic/contract-data/class-definition-projection.json",
              "de4sdv.o4-definition-projection/v1",
              "de4sdv/semantic/contract-data/class-definition-profile.json",
              "de4sdv.o4-definition-profile/v1"),
    LayerSpec("o2plus",
              "de4sdv/semantic/contract-data/native-grounding-projection.json",
              "de4sdv.semantic-projection.o2plus/v1",
              "de4sdv/semantic/contract-data/native-grounding-profile.json",
              "de4sdv.api-representation-profile.o2plus/v1"),
    LayerSpec("vocabulary-carrier",
              "de4sdv/semantic/contract-data/increment-relationship-projection.json",
              "de4sdv.vocabulary-carrier-projection/v1",
              "de4sdv/semantic/contract-data/increment-relationship-profile.json",
              "de4sdv.vocabulary-carrier-profile/v1"),
)

#: Definition-admission batch 2 (generator and schema owned by the admission
#: lane: ``de4sdv.o4-definition-batch2-projection/v1`` + ``-profile/v1``). It is
#: optional only while the pair is absent from the checkout; once present it
#: is bound like every other layer. Rows flow through :func:`_batch2_provider`.
BATCH2_LAYER = LayerSpec("definition-batch2",
                         "de4sdv/semantic/contract-data/kernel-vocabulary-projection.json",
                         "de4sdv.o4-definition-batch2-projection/v1",
                         "de4sdv/semantic/contract-data/kernel-vocabulary-profile.json",
                         "de4sdv.o4-definition-batch2-profile/v1",
                         required=False)
BATCH2_LAYERS: tuple[LayerSpec, ...] = (BATCH2_LAYER,)


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _canonical_digest(value: Any) -> str:
    return _sha256_bytes(canonical_json(value).encode("utf-8"))


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        document[key] = value
    return document


def _read_json(root: Path, relative: str, schema: str) -> tuple[dict[str, Any], bytes]:
    path = Path(root) / relative
    try:
        raw = path.read_bytes()
        document = json.loads(raw, object_pairs_hook=_unique_json_object)
    except (OSError, ValueError) as exc:
        raise ModelAuthorityRefused(f"projection layer file unreadable: {relative}: {exc}") from exc
    if not isinstance(document, dict) or document.get("schema") != schema:
        raise ModelAuthorityRefused(f"projection layer schema mismatch: {relative}")
    return document, raw


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ModelAuthorityRefused(f"{label}: expected an object, got {value!r}")
    return value


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ModelAuthorityRefused(f"{label}: malformed string token {value!r}")
    return value


def _row_identity(row: Mapping[str, Any]) -> str:
    row = _object(row, "projection/profile record")
    identities = [_token(row[key], f"record {key}")
                  for key in ("identity", "for_identity", "for_concept") if key in row]
    if not identities or len(set(identities)) != 1:
        raise ModelAuthorityRefused(f"record has missing or conflicting identities: {identities!r}")
    return identities[0]


@dataclass(frozen=True)
class Provision:
    """One provider's answer for one identity."""

    identity: str
    kind: str  # "class" | "relationship"
    layer: str
    mapping: Any = None  # Kernel*Mapping for classes
    spec: Any = None  # relationship spec (ontology-shaped dict)
    relationship: RelationshipMapping | None = None


_SEMANTIC_ROW_FIELDS = frozenset({
    "identity", "semantic_kind", "category", "construct", "definition", "grounding",
    "domain", "range", "direction", "semantic_strength", "support", "traversal", "outputs",
    "claim_boundary", "accounting", "admission_class", "boundary", "carrier", "relation",
    "retired", "successor", "structure", "support_state", "model_evidence",
})
_ROW_PROVENANCE_FIELDS = frozenset({"wave", "register_wave", "review_ref", "accepted_ref", "api_identity"})
_SEMANTIC_PROFILE_FIELDS = frozenset({
    "identity", "for_identity", "for_concept", "profile_identity", "representation_class",
    "binding_contract_echo", "witness_forms", "representation", "carrier", "mechanics",
    "configurator_authority", "external_reference", "retired_resolution", "serializer_mechanics",
    "successor_mechanics", "api_metaclass_note", "api_metaclasses", "library_grounding_mechanics",
    "resolution", "runtime_mapping_state", "runtime_mapping_note", "semantic_contract_echo",
})
_PROFILE_PROVENANCE_FIELDS = frozenset({"mechanics_source", "mechanics_refs"})

# Document wrappers are meaning too, not a catch-all metadata envelope.
_DOCUMENT_COMMON_FIELDS = frozenset({"schema", "status", "warning"})
_PROJECTION_DOCUMENT_FIELDS = {
    "definition": _DOCUMENT_COMMON_FIELDS | {"scope", "rows"},
    "definition-batch2": _DOCUMENT_COMMON_FIELDS | {"scope", "rows"},
    "o2plus": _DOCUMENT_COMMON_FIELDS | {"scope", "rows"},
    "vocabulary-carrier": _DOCUMENT_COMMON_FIELDS | {"candidates", "admitted", "rows"},
}
_PROFILE_DOCUMENT_FIELDS = _DOCUMENT_COMMON_FIELDS | {"entries"}
_DOCUMENT_PROVENANCE_FIELDS = frozenset({"binding"})


def _semantic_document(document: Mapping[str, Any], spec: LayerSpec, *,
                       profile: bool) -> dict[str, Any]:
    fields = _PROJECTION_DOCUMENT_FIELDS.get(spec.name)
    if fields is None:
        raise ModelAuthorityRefused(f"unsupported live projection layer: {spec.name}")
    if profile:
        fields = _PROFILE_DOCUMENT_FIELDS
    unknown = set(document) - fields - _DOCUMENT_PROVENANCE_FIELDS
    if unknown:
        raise ModelAuthorityRefused("unclassified semantic document fields: " + ", ".join(sorted(unknown)))
    # Collections have their own closed record contract and order-independent digest.
    return {key: json.loads(json.dumps(document[key])) for key in fields - {"rows", "entries"}
            if key in document}


def _semantic_record(record: Mapping[str, Any], fields: frozenset[str],
                     provenance: frozenset[str]) -> dict[str, Any]:
    """Select declared meaning; unknown fields require explicit classification.

    All nested values of semantic fields are kept, except the explicitly named
    toolchain receipt in ``representation.toolchain`` and review pointer in
    ``external_reference.accepted_ref``. Definition text, source/declaration
    witnesses, disjointness and representation rules are NOT mere metadata just
    because runtime traversal does not consume them.
    """
    unknown = set(record) - fields - provenance
    if unknown:
        raise ModelAuthorityRefused("unclassified semantic record fields: " + ", ".join(sorted(unknown)))
    value = {key: json.loads(json.dumps(record[key])) for key in fields if key in record}
    for key, excluded in (("representation", "toolchain"), ("external_reference", "accepted_ref")):
        if isinstance(value.get(key), dict):
            value[key].pop(excluded, None)
    return value


def _provisions_digest(provisions: list[Provision], *, rows: list[Mapping[str, Any]],
                       entries: list[Mapping[str, Any]],
                       documents: Mapping[str, Any] | None = None) -> str:
    """Digest decoded providers AND explicitly declared projection/profile meaning.

    Covers definitions, source pins, lineage/disjointness, domain/range/direction,
    strength/support/claim boundaries, carrier/discriminator pins, serializer
    mechanics and retired resolutions. Review references, API-UUID claims,
    implementation pointers and toolchain receipts are separate provenance.
    Document binding blocks, byte hashes and Git source revisions never enter.
    Record/JSON object order is incidental; nested semantic list order is kept.
    """
    return _canonical_digest({
        "providers": [asdict(p) for p in sorted(provisions, key=lambda p: (p.identity, p.kind, p.layer))],
        "rows": sorted((_semantic_record(row, _SEMANTIC_ROW_FIELDS, _ROW_PROVENANCE_FIELDS)
                        for row in rows), key=canonical_json),
        "entries": sorted((_semantic_record(entry, _SEMANTIC_PROFILE_FIELDS, _PROFILE_PROVENANCE_FIELDS)
                           for entry in entries), key=canonical_json),
        **({"documents": documents} if documents is not None else {}),
    })


def _file_mapping(contract: Any, identity: str) -> KernelFileMapping:
    if not isinstance(contract, Mapping):
        raise ModelAuthorityRefused(f"{identity}: missing kernel binding contract")
    source_file = contract.get("source_file", contract.get("file"))
    declaration = contract.get("declaration")
    if (not isinstance(source_file, str) or not source_file.strip()
            or not isinstance(declaration, str) or not declaration.strip()):
        raise ModelAuthorityRefused(f"{identity}: incomplete file/declaration contract")
    try:
        declaration_identity(declaration)
    except ValueError as exc:
        raise ModelAuthorityRefused(f"{identity}: malformed declaration {declaration!r}") from exc
    return KernelFileMapping(source_file, declaration)


def _definition_row_provider(row: Mapping[str, Any], entry: Mapping[str, Any] | None,
                             layer: str) -> Provision:
    """Batch-1 definition rows: ``semantic_kind: class`` with a kernel binding contract."""
    identity = _row_identity(row)
    kind = _token(row.get("semantic_kind", "class"), f"{identity}: semantic_kind")
    if kind != "class":
        raise ModelAuthorityRefused(
            f"{identity}: unsupported definition row semantic_kind {kind!r}")
    grounding = _object(row.get("grounding"), f"{identity}: grounding")
    return Provision(identity, "class", layer,
                     mapping=_file_mapping(grounding.get("kernel_binding_contract"), identity))


_BATCH2_CLASS_ADMISSIONS = frozenset({"definition", "external-reference"})
_BATCH2_RELATION_ADMISSIONS = frozenset({
    "relationship-vocabulary", "relationship-runtime", "external-reference",
    "successor", "retired-name"})


def _batch2_class(identity: str, row: Mapping[str, Any], layer: str) -> Provision:
    grounding = _object(row.get("grounding"), f"{identity}: grounding")
    kinds = [key for key in ("kernel_binding_contract", "kernel_native", "kernel_external")
             if grounding.get(key)]
    if len(kinds) != 1:
        raise ModelAuthorityRefused(
            f"{identity}: batch-2 class row needs exactly one kernel grounding, got {kinds}")
    value = grounding[kinds[0]]
    relations = _object(grounding.get("ontology_relations", {}), f"{identity}: ontology_relations")
    parent = relations.get("sub_class_of")
    spec = {"sub_class_of": _token(parent, f"{identity}: sub_class_of")} if parent is not None else None
    if kinds[0] == "kernel_binding_contract":
        return Provision(identity, "class", layer, mapping=_file_mapping(value, identity), spec=spec)
    value = _token(value, f"{identity}: {kinds[0]} grounding")
    mapping = KernelNativeMapping(value) if kinds[0] == "kernel_native" else KernelExternalMapping(value)
    return Provision(identity, "class", layer, mapping=mapping, spec=spec)


def _batch2_discriminator(identity: str, range_: Mapping[str, Any]) -> dict[str, Any] | None:
    discriminator = range_.get("discriminator")
    if discriminator is None:
        return None
    closure = discriminator.get("closure") if isinstance(discriminator, Mapping) else None
    if (not isinstance(discriminator, Mapping) or discriminator.get("kind") != "type-lineage"
            or not isinstance(closure, list)):
        raise ModelAuthorityRefused(f"{identity}: malformed range discriminator")
    if (identity in DISCRIMINATED_PREDICATES
            and len(closure) != EXPECTED_EVIDENCE_CONTRACT_DEFINITIONS):
        raise ModelAuthorityRefused(
            f"{identity}: discriminator closure has {len(closure)} definitions, expected "
            f"{EXPECTED_EVIDENCE_CONTRACT_DEFINITIONS}")
    _file_mapping(discriminator.get("lineage"), identity)
    for member in closure:
        _file_mapping(member, identity)
    return json.loads(json.dumps(dict(discriminator)))


def bound_evidence_contract_closure(root: Path = ROOT) -> list[dict[str, str]]:
    """The bound ``hasRelevantEvidenceContract`` closure members (file, declaration)."""
    _, provisions = load_model_layers(root)
    for provision in provisions:
        if provision.identity in DISCRIMINATED_PREDICATES and provision.kind == "relationship":
            discriminator = (provision.spec or {}).get("range_discriminator") or {}
            members = []
            for member in discriminator.get("closure") or ():
                pinned = _file_mapping(member, provision.identity)
                members.append({"source_file": pinned.file, "declaration": pinned.declaration})
            if len(members) == EXPECTED_EVIDENCE_CONTRACT_DEFINITIONS:
                return sorted(members, key=lambda m: (m["source_file"], m["declaration"]))
    raise ModelAuthorityRefused(
        "no bound EvidenceContract closure: the batch-2 hasRelevantEvidenceContract "
        f"discriminator with {EXPECTED_EVIDENCE_CONTRACT_DEFINITIONS} members is not projected")


class _ClosureMemberContract:
    """Bound closure members presented to the ingestion binding validator."""

    def __init__(self, members: list[Mapping[str, str]]) -> None:
        self._mappings = {f"{m['source_file']}::{m['declaration']}":
                          KernelFileMapping(m["source_file"], m["declaration"]) for m in members}
        self.classes = list(self._mappings)

    def mapping(self, key: str) -> KernelFileMapping:
        return self._mappings[key]


def validate_closure_members(members: list[Mapping[str, str]], elements: list[Mapping[str, Any]],
                             element_sources: Mapping[str, str]) -> list[dict[str, str]]:
    """Element id of each bound closure member through the ingestion binding rule.

    Reuses :func:`validation.validate_ontology_bindings` (API type + declared
    name + serializer-recorded source file over the same-run export): the
    rule that establishes kernel identity at ingestion (ADR 0011). Unresolved
    or ambiguous members refuse.
    """
    from .validation import validate_ontology_bindings

    report = validate_ontology_bindings(_ClosureMemberContract(list(members)),
                                        [dict(e) for e in elements], dict(element_sources))
    validated, problems = [], []
    for entry in report.entries:
        if entry.status != "mapped" or len(entry.element_ids) != 1:
            problems.append(f"{entry.ontology_class}: {entry.status} ({entry.detail})")
            continue
        validated.append({**entry.mapping, "element_id": entry.element_ids[0]})
    if problems:
        raise ModelAuthorityRefused("bound EvidenceContract closure members are not validated: "
                                    + "; ".join(problems))
    return [{"source_file": m["file"], "declaration": m["declaration"], "element_id": m["element_id"]}
            for m in sorted(validated, key=lambda m: (m["file"], m["declaration"]))]


def _batch2_relation(identity: str, row: Mapping[str, Any], entry: Mapping[str, Any] | None,
                     layer: str) -> Provision:
    admission = row.get("admission_class")
    support = _token(row.get("support", "vocabulary-only"), f"{identity}: support")
    if admission == "successor":
        successor = _object(row.get("successor"), f"{identity}: successor")
        end_pairs = successor.get("end_pairs")
        if not isinstance(end_pairs, list) or not end_pairs:
            raise ModelAuthorityRefused(f"{identity}: successor row lacks its end pairs")
        pairs = []
        for pair in end_pairs:
            pair = _object(pair, f"{identity}: successor end pair")
            pairs.append([_token(pair.get(key), f"{identity}: successor {key}")
                          for key in ("source_class", "target_class")])
        return Provision(identity, "relationship", layer,
                         spec={"end_pairs": pairs, "support": support})
    relation = _object(row.get("relation"), f"{identity}: relation")
    domain_record = _object(relation.get("domain"), f"{identity}: relation domain")
    range_record = _object(relation.get("range"), f"{identity}: relation range")
    domain = _token(domain_record.get("ontology_class"), f"{identity}: domain ontology_class")
    range_ = _token(range_record.get("ontology_class"), f"{identity}: range ontology_class")
    strength = relation.get("semantic_strength")
    if strength is not None:
        strength = _token(strength, f"{identity}: semantic_strength")
    if admission == "retired-name":
        retired = _object(row.get("retired"), f"{identity}: retired")
        resolution = _object((entry or {}).get("retired_resolution"), f"{identity}: retired_resolution")
        spec = {"successor": _token(retired.get("successor"), f"{identity}: retired successor"),
                "navigation": _token(retired.get("successor_navigation"), f"{identity}: retired navigation"),
                "refusal": _token(retired.get("refusal"), f"{identity}: retired refusal"),
                "profile_successor": _token(resolution.get("successor"), f"{identity}: profile successor"),
                "profile_navigation": _token(resolution.get("navigation"), f"{identity}: profile navigation")}
        return Provision(identity, "retired", layer, spec=spec)
    spec: dict[str, Any] = {"domain": domain, "range": range_,
                            "support": support}
    if strength is not None:
        spec["semantic_strength"] = strength
    discriminator = _batch2_discriminator(identity, range_record)
    if discriminator is not None:
        spec["range_discriminator"] = discriminator
    carrier = row.get("carrier")
    if carrier is not None:
        pinned = _file_mapping(carrier, identity)
        spec["carrier"] = {"file": pinned.file, "declaration": pinned.declaration}
    mechanics = dict(_object((entry or {}).get("serializer_mechanics", {}), f"{identity}: serializer_mechanics"))
    if "strategy" not in mechanics:
        return Provision(identity, "relationship", layer, spec=spec)
    strategy = _token(mechanics.pop("strategy"), f"{identity}: serializer strategy")
    if not strength:
        raise ModelAuthorityRefused(f"{identity}: serialized relationship lacks a semantic strength")
    mapping = RelationshipMapping(name=identity, strategy=strategy, semantic_strength=strength,
                                  configuration=mechanics, domain=domain, range=range_)
    spec["sysml_mapping"] = {"strategy": strategy, **mechanics}
    return Provision(identity, "relationship", layer, spec=spec, relationship=mapping)


def _batch2_provider(row: Mapping[str, Any], entry: Mapping[str, Any] | None,
                     layer: str) -> Provision:
    """Definition-admission batch-2 rows (every admission class B1 emits).

    Unknown shapes are refused rather than guessed.
    """
    identity = _row_identity(row)
    if entry is None:
        raise ModelAuthorityRefused(f"{identity}: batch-2 row has no profile entry")
    kind = _token(row.get("semantic_kind"), f"{identity}: semantic_kind")
    admission = _token(row.get("admission_class"), f"{identity}: admission_class")
    if kind == "class" and admission in _BATCH2_CLASS_ADMISSIONS:
        return _batch2_class(identity, row, layer)
    if kind == "relationship" and admission in _BATCH2_RELATION_ADMISSIONS:
        return _batch2_relation(identity, row, entry, layer)
    raise ModelAuthorityRefused(
        f"{identity}: unsupported batch-2 semantic_kind/admission_class "
        f"{kind!r}/{admission!r}")


_RELATIONSHIP_O2P = frozenset({"usesVerificationMethod"})


def _o2plus_provider(row: Mapping[str, Any], layer: str) -> Provision:
    identity = _row_identity(row)
    category = _token(row.get("category"), f"{identity}: O2+ category")
    construct = _token(row.get("construct"), f"{identity}: O2+ construct")
    if identity in _RELATIONSHIP_O2P or row.get("semantic_kind") == "relationship":
        spec = {"support": _token(row.get("support", "vocabulary-only"), f"{identity}: support"),
                "construct": construct}
        return Provision(identity, "relationship", layer, spec=spec)
    if category == "native":
        return Provision(identity, "class", layer, mapping=KernelNativeMapping(construct))
    if category == "library-mapped-native":
        return Provision(identity, "class", layer, mapping=KernelExternalMapping(construct))
    if category == "model-resident-vocabulary":
        grounding = _object(row.get("grounding"), f"{identity}: O2+ grounding")
        witness = _object(grounding.get("witness"), f"{identity}: O2+ witness")
        contains = _token(witness.get("contains"), f"{identity}: witness contains")
        if contains.endswith("{"):
            contains = contains[:-1].strip()
        return Provision(identity, "class", layer,
                         mapping=_file_mapping({"file": witness.get("file"),
                                                "declaration": contains}, identity))
    raise ModelAuthorityRefused(f"{identity}: unsupported O2+ category {category!r}")


def _carrier_provider(row: Mapping[str, Any], layer: str) -> Provision:
    identity = _row_identity(row)
    domain_record = _object(row.get("domain"), f"{identity}: carrier domain")
    range_record = _object(row.get("range"), f"{identity}: carrier range")
    domain = _token(domain_record.get("identity"), f"{identity}: domain identity")
    range_ = _token(range_record.get("identity"), f"{identity}: range identity")
    carrier = _file_mapping(row.get("carrier"), identity)
    spec = {"domain": domain, "range": range_,
            "carrier": {"file": carrier.file, "declaration": carrier.declaration},
            "support": _token(row.get("support", "vocabulary-only"), f"{identity}: support")}
    return Provision(identity, "relationship", layer, spec=spec)


def _live_record_index(document: Mapping[str, Any], spec: LayerSpec, *,
                       profile: bool) -> dict[str, Mapping[str, Any]]:
    section, role = ("entries", "profile") if profile else ("rows", "projection")
    records = document.get(section)
    if not isinstance(records, list) or (not profile and not records):
        raise ModelAuthorityRefused(f"{spec.name}: {section} must be a list" +
                                    ("" if profile else " of nonempty projection rows"))
    fields = _SEMANTIC_PROFILE_FIELDS if profile else _SEMANTIC_ROW_FIELDS
    provenance = _PROFILE_PROVENANCE_FIELDS if profile else _ROW_PROVENANCE_FIELDS
    indexed = {}
    for record in records:
        record = _object(record, f"{spec.name}: {role} record")
        _semantic_record(record, fields, provenance)
        identity = _row_identity(record)
        if identity in indexed:
            raise ModelAuthorityRefused(f"{spec.name}: duplicate {role} identity: {identity}")
        indexed[identity] = record
    return indexed


def _layer_provisions(spec: LayerSpec, projection: dict[str, Any],
                      profile: dict[str, Any]) -> list[Provision]:
    rows = _live_record_index(projection, spec, profile=False)
    entries = _live_record_index(profile, spec, profile=True)
    required = set(rows)
    if spec.name == "o2plus":
        required = set()
        for identity, row in rows.items():
            outputs = _object(row.get("outputs", {}), f"{identity}: outputs")
            for flag in ("api_profile_required", "api_profile_entry"):
                if flag in outputs and not isinstance(outputs[flag], bool):
                    raise ModelAuthorityRefused(f"{identity}: outputs.{flag} must be boolean")
                if outputs.get(flag) is True:
                    required.add(identity)
    orphan = set(entries) - set(rows)
    if orphan:
        raise ModelAuthorityRefused(f"{spec.name}: orphan profile identities: {sorted(orphan)}")
    missing = required - set(entries)
    if missing:
        raise ModelAuthorityRefused(f"{spec.name}: missing required profile identities: {sorted(missing)}")
    result = []
    for identity, row in rows.items():
        if spec.name == "o2plus":
            result.append(_o2plus_provider(row, spec.name))
        elif spec.name == "vocabulary-carrier":
            result.append(_carrier_provider(row, spec.name))
        elif spec.name == BATCH2_LAYER.name:
            result.append(_batch2_provider(row, entries.get(identity), spec.name))
        else:
            result.append(_definition_row_provider(row, entries.get(identity), spec.name))
    return result


def _read_projection_layers(root: Path, specs: tuple[LayerSpec, ...]) -> tuple[list[dict[str, Any]], list[Provision]]:
    """Read live semantic outputs, with byte provenance separate from meaning.

    No live commit binding is required. ``sha256`` in the file records remains
    diagnostic raw-byte provenance; ``semantic_sha256`` digests declared meaning
    and is the only layer digest allowed into semantic-authority identity.
    """
    records: list[dict[str, Any]] = []
    provisions: list[Provision] = []
    for spec in specs:
        if not spec.required and not (Path(root) / spec.projection_path).exists():
            continue
        projection, projection_raw = _read_json(root, spec.projection_path, spec.projection_schema)
        profile, profile_raw = _read_json(root, spec.profile_path, spec.profile_schema)
        documents = {"projection": _semantic_document(projection, spec, profile=False),
                     "profile": _semantic_document(profile, spec, profile=True)}
        layer_provisions = _layer_provisions(spec, projection, profile)
        records.append({
            "layer": spec.name,
            "semantic_sha256": _provisions_digest(layer_provisions, rows=projection["rows"],
                                                   entries=profile.get("entries") or [],
                                                   documents=documents),
            "projection": {"path": spec.projection_path, "schema": spec.projection_schema,
                           "sha256": _sha256_bytes(projection_raw)},
            "profile": {"path": spec.profile_path, "schema": spec.profile_schema,
                        "sha256": _sha256_bytes(profile_raw)},
            "identities": sorted(p.identity for p in layer_provisions),
        })
        provisions.extend(layer_provisions)
    return records, provisions


def load_projection_layers(root: Path = ROOT) -> tuple[list[dict[str, Any]], list[Provision]]:
    """Read the complete live layer set for runtime construction."""
    return _read_projection_layers(root, LAYERS + BATCH2_LAYERS)


def _successor_names(contract: Mapping[str, Any]) -> dict[str, str]:
    """Successor relation identity -> canonical name (inverses included)."""
    names = {}
    for name, rows in contract["relations"].items():
        names[name] = name
        inverse = rows[0].get("inverse")
        if inverse:
            names[inverse] = name
    return names


@dataclass(frozen=True)
class Routing:
    providers: Mapping[str, Provision]
    corroborations: Mapping[str, tuple[str, ...]]
    duplicates: tuple[str, ...]
    residual: Mapping[str, str]
    #: Retired names (owner decision D4): name -> the successor navigation the
    #: refusal points to ("retired; use <navigation>").
    retired_names: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    def record(self) -> dict[str, Any]:
        return {
            "schema": ROUTING_SCHEMA,
            "providers": {name: p.layer for name, p in sorted(self.providers.items())},
            "corroborations": {k: list(v) for k, v in sorted(self.corroborations.items())},
            "duplicates": list(self.duplicates),
            "residual": dict(sorted(self.residual.items())),
            "retired_names": dict(sorted(self.retired_names.items())),
        }


def _successor_provisions(contract: Mapping[str, Any]) -> list[Provision]:
    result = []
    for name, pin in contract["classes"].items():
        result.append(Provision(name, "class", "successor-contract",
                                mapping=_file_mapping(pin, name)))
    for name, rows in contract["relations"].items():
        first = rows[0]
        mapping = RelationshipMapping(name, "successor", first["strength"], {},
                                      first["sourceClass"], first["targetClass"])
        spec = {"sysml_mapping": {"strategy": "successor"},
                "end_pairs": [[r["sourceClass"], r["targetClass"]] for r in rows]}
        result.append(Provision(name, "relationship", "successor-contract",
                                spec=spec, relationship=mapping))
        if first.get("inverse"):
            inverse = first["inverse"]
            result.append(Provision(inverse, "relationship", "successor-contract",
                                    spec={"sysml_mapping": {"strategy": "successor"},
                                          "inverse_of": name},
                                    relationship=RelationshipMapping(
                                        inverse, "successor", first["strength"], {},
                                        first["targetClass"], first["sourceClass"])))
    return result


def _corroborates(existing: Provision, candidate: Provision, contract: Mapping[str, Any]) -> bool:
    """Two providers may coexist only when they provably agree."""
    if existing.kind != candidate.kind:
        return False
    if existing.kind == "class":
        return existing.mapping == candidate.mapping
    if candidate.layer == "successor-contract":
        successor, other = candidate, existing
    elif existing.layer == "successor-contract":
        successor, other = existing, candidate
    else:
        return False
    pairs = {tuple(pair) for pair in (successor.spec or {}).get("end_pairs", ())}
    spec = other.spec or {}
    if "end_pairs" in spec:  # a successor row: the exact end-pair set must agree
        return bool(pairs) and {tuple(pair) for pair in spec["end_pairs"]} == pairs
    return bool(pairs) and (spec.get("domain"), spec.get("range")) in pairs


def _lineage_pin(name: str, pin: Provision, provisions: list[Provision]) -> bool:
    """The pin is the mapping of exactly one projected direct specialization."""
    children = [p for p in provisions if p.kind == "class" and p.layer == BATCH2_LAYER.name
                and (p.spec or {}).get("sub_class_of") == name
                and isinstance(p.mapping, KernelFileMapping)]
    return len(children) == 1 and children[0].mapping == pin.mapping


def _retired_disagreement(provision: Provision, contract: Mapping[str, Any]) -> str | None:
    """A batch-2 retired-name row must match a model retirement record and
    name an existing successor navigation (owner decision D4)."""
    spec = provision.spec or {}
    if provision.identity not in (contract.get("retired") or {}):
        return "has no model successor retirement record"
    navigations = _successor_names(contract)
    navigation = spec.get("navigation")
    if spec.get("successor") not in contract.get("relations", {}):
        return f"names successor {spec.get('successor')!r}, which is not a successor relation"
    if navigation not in navigations or navigations[navigation] != spec.get("successor"):
        return f"names navigation {navigation!r}, which is not a navigation of {spec.get('successor')!r}"
    if (spec.get("profile_successor"), spec.get("profile_navigation")) != (spec.get("successor"), navigation):
        return "profile retired resolution differs from the projection row"
    if spec.get("refusal") != f"retired; use {navigation}":
        return f"refusal {spec.get('refusal')!r} is not 'retired; use {navigation}'"
    return None


def compute_routing(*, provisions: list[Provision], successor_contract: Mapping[str, Any],
                    register_rows: Mapping[str, Mapping[str, Any]] | None = None,
                    seed: list[Provision] | None = None) -> Routing:
    """Disjoint provider routing; duplicates are recorded (and refused by callers).

    ``seed`` are the fixed first providers (the frozen O2-chain layer); no
    later layer may re-provide a seeded identity. The residual is every
    retained register row no layer provides (it must be empty: the coverage
    gate and the facade construction refuse a non-empty residual).
    """
    providers: dict[str, Provision] = {}
    corroborations: dict[str, list[str]] = {}
    duplicates: list[str] = []
    seed = list(seed or ())
    seed_layers = {provision.layer for provision in seed}
    for provision in seed:
        providers[provision.identity] = provision
    retired = set(successor_contract.get("retired") or ())
    retired_names: dict[str, Provision] = {}
    ordered = list(provisions)
    for successor in _successor_provisions(successor_contract):
        existing = providers.get(successor.identity)
        if existing is not None and existing.layer not in seed_layers and _corroborates(
                existing, successor, successor_contract):
            # Successor relations own traversal; layer rows corroborate them.
            if successor.kind == "relationship":
                providers[successor.identity] = successor
                corroborations.setdefault(successor.identity, []).append(existing.layer)
            else:
                corroborations.setdefault(successor.identity, []).append(successor.layer)
            continue
        ordered.append(successor)
    for provision in ordered:
        name = provision.identity
        if provision.kind == "retired":
            problem = _retired_disagreement(provision, successor_contract)
            if problem:
                duplicates.append(f"{name}: {provision.layer} retired name {problem}")
            else:
                retired_names[name] = provision
                corroborations.setdefault(name, []).append(provision.layer)
            continue
        if name in retired:
            duplicates.append(f"{name}: retired name provided by {provision.layer}")
            continue
        existing = providers.get(name)
        if existing is None:
            providers[name] = provision
            continue
        if (existing.layer == BATCH2_LAYER.name and provision.layer == "successor-contract"
                and provision.kind == "class"
                and _lineage_pin(name, provision, provisions)):
            # Endpoint lineage pin (relationship_successor_contract): the class is
            # natively represented and the successor contract pins its unique
            # file-mapped specialization. The successor pin owns the runtime
            # mapping (as in the approved successor runtime); the batch-2 row
            # corroborates it through its projected sub_class_of.
            providers[name] = provision
            corroborations.setdefault(name, []).append(existing.layer)
            continue
        if existing.layer not in seed_layers and _corroborates(existing, provision, successor_contract):
            if provision.layer == "successor-contract" and provision.kind == "relationship":
                providers[name] = provision
                corroborations.setdefault(name, []).append(existing.layer)
            else:
                corroborations.setdefault(name, []).append(provision.layer)
            continue
        duplicates.append(f"{name}: {existing.layer} and {provision.layer}")
    residual: dict[str, str] = {}
    for name, row in sorted((register_rows or {}).items()):
        if row.get("accounting_status") != "retained" or name in providers or name in retired:
            continue
        residual[name] = ("no model projection layer provides this retained register row "
                          f"(migration_class={row.get('migration_class')}, "
                          f"final_disposition={row.get('final_disposition')})")
    return Routing(MappingProxyType(providers),
                   MappingProxyType({k: tuple(v) for k, v in corroborations.items()}),
                   tuple(sorted(duplicates)), MappingProxyType(residual),
                   MappingProxyType({name: str(p.spec["navigation"])
                                     for name, p in sorted(retired_names.items())}))


def load_register_rows(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    path = Path(root) / "de4sdv/semantic/contract-data/ontology-identity-register.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    return {row["identity"]: row for row in document["rows"]}



# ---------------------------------------------------------------------------
# Frozen O2-chain layer
# ---------------------------------------------------------------------------


def o2_chain_records(root: Path = ROOT) -> list[dict[str, Any]]:
    """Path, schema, source revision and sha256 of every frozen chain file."""
    records = []
    for relative, schema in O2_PROJECTION_CHAIN + O2_PROFILE_CHAIN:
        path = Path(root) / relative
        try:
            raw = path.read_bytes()
            document = json.loads(raw)
        except (OSError, ValueError) as exc:
            raise ModelAuthorityRefused(f"frozen O2-chain record unreadable: {relative}: {exc}") from exc
        if not isinstance(document, dict) or document.get("schema") != schema:
            raise ModelAuthorityRefused(f"frozen O2-chain record schema mismatch: {relative}")
        records.append({"path": relative, "schema": schema,
                        "source_revision": str((document.get("binding") or {}).get("source_revision") or ""),
                        "sha256": _sha256_bytes(raw)})
    return records


def load_o2_chain_rows(root: Path = ROOT) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Projection rows and profile entries of the frozen chain (later wins)."""
    rows: dict[str, dict[str, Any]] = {}
    entries: dict[str, dict[str, Any]] = {}
    for relative, _schema in O2_PROJECTION_CHAIN:
        document = json.loads((Path(root) / relative).read_text(encoding="utf-8"))
        for section in ("concepts", "predicates"):
            for row in document.get(section, []):
                identity = row.get("identity") or row.get("for_concept")
                if identity:
                    rows[identity] = row
    for relative, _schema in O2_PROFILE_CHAIN:
        document = json.loads((Path(root) / relative).read_text(encoding="utf-8"))
        for entry in document.get("profiles", []):
            identity = entry.get("for_identity") or entry.get("for_concept")
            if identity:
                entries[identity] = entry
    return rows, entries


def o2_chain_provisions(root: Path = ROOT) -> list[Any]:
    """The 13 migrated identities as providers from the frozen O2 chain.

    Same construction as the O3 authority facade: semantics from the
    Semantic Projection row, mechanics from the Representation Profile entry;
    a partial provider is refused.
    """
    rows, entries = load_o2_chain_rows(root)
    provisions = []
    for name in O2_CHAIN_RELATIONSHIPS:
        row, entry = rows.get(name), entries.get(name)
        if row is None or entry is None:
            raise ModelAuthorityRefused(f"frozen O2-chain identity {name!r} lacks a Projection row or Profile entry")
        relation = row.get("relation") or {}
        mechanics = dict(entry.get("serializer_mechanics") or {})
        strategy = str(mechanics.pop("strategy", "") or "")
        mechanics.pop("semantic_strength", None)
        domain = str((relation.get("domain") or {}).get("ontology_class") or "")
        range_ = str((relation.get("range") or {}).get("ontology_class") or "")
        strength = str(relation.get("semantic_strength") or "")
        if not strategy or not domain or not range_ or not strength:
            raise ModelAuthorityRefused(f"frozen O2-chain identity {name!r} lacks a complete declaration")
        mapping = RelationshipMapping(name=name, strategy=strategy, semantic_strength=strength,
                                      configuration=mechanics, domain=domain, range=range_)
        spec = {"sysml_mapping": {"strategy": strategy, **mechanics}, "domain": domain,
                "range": range_, "semantic_strength": strength}
        provisions.append(Provision(name, "relationship", O2_CHAIN_LAYER, spec=spec,
                                    relationship=mapping))
    for name in O2_CHAIN_CLASSES:
        row = rows.get(name)
        if row is None:
            raise ModelAuthorityRefused(f"frozen O2-chain class {name!r} lacks a Projection row")
        if name == "VerificationCase":
            construct = row.get("construct") or {}
            native = str((construct.get("native_grounding") or {}).get("identity") or "")
            if str(construct.get("kind") or "") != "native" or not native:
                raise ModelAuthorityRefused("VerificationCase frozen O2-chain row lacks native grounding")
            mapping: Any = KernelNativeMapping(native)
        else:
            contract = (row.get("grounding") or {}).get("kernel_binding_contract") or {}
            source_file = str(contract.get("source_file") or "")
            declaration = str(contract.get("declaration") or "")
            if not source_file or not declaration:
                raise ModelAuthorityRefused(f"frozen O2-chain class {name!r} lacks a file/declaration grounding")
            mapping = KernelFileMapping(source_file, declaration)
        provisions.append(Provision(name, "class", O2_CHAIN_LAYER, mapping=mapping))
    return provisions


# ---------------------------------------------------------------------------
# Successor class pins from the layers
# ---------------------------------------------------------------------------


def model_class_pins(provisions: list[Any]) -> dict[str, dict[str, str]]:
    """Exact file/declaration pin per class, from the projected class mappings.

    A file-mapped class pins its own declaration. A natively represented or
    external class is pinned by its unique directly specializing file-mapped
    class (the projected ``sub_class_of`` relation); two such specializations
    are ambiguous and pin nothing. Same rule as the predecessor ontology pins.
    """
    pins: dict[str, dict[str, str]] = {}
    parents: dict[str, str] = {}
    unpinned: set[str] = set()
    for provision in provisions:
        if provision.kind != "class":
            continue
        if isinstance(provision.mapping, KernelFileMapping):
            pins[provision.identity] = {"file": provision.mapping.file,
                                        "declaration": provision.mapping.declaration}
        else:
            unpinned.add(provision.identity)
        parent = (provision.spec or {}).get("sub_class_of") if isinstance(provision.spec, dict) else None
        if isinstance(parent, str) and parent:
            parents[provision.identity] = parent
    for name in sorted(unpinned):
        children = [pins[child] for child, parent in parents.items()
                    if parent == name and child in pins]
        if len(children) == 1:
            pins[name] = dict(children[0])
    return pins


def _pin_inputs(records: list[dict[str, Any]]) -> tuple[str, ...]:
    inputs = []
    for record in records:
        if record.get("layer") == O2_CHAIN_LAYER:
            inputs.extend(item["path"] for item in record["chain"])
        else:
            inputs.extend((record["projection"]["path"], record["profile"]["path"]))
    return tuple(sorted(set(inputs)))


def generate_model_successor_contract(root: Path = ROOT, *, records=None,
                                      provisions=None) -> dict[str, Any]:
    """The successor contract with class pins from the projection layers."""
    from .relationship_successor_contract import generate_contract, verify_contract

    if records is None or provisions is None:
        records, provisions = load_model_layers(root)
    pins = model_class_pins(provisions)
    inputs = _pin_inputs(records)
    contract = generate_contract(Path(root), class_pins=pins, pin_inputs=inputs)
    verify_contract(contract, Path(root), class_pins=pins, pin_inputs=inputs)
    return contract


# ---------------------------------------------------------------------------
# Layers, refusals, exclusions
# ---------------------------------------------------------------------------


def load_model_layers(root: Path = ROOT) -> tuple[list[dict[str, Any]], list[Any]]:
    """Every layer the model contract is built from: (records, provisions).

    The frozen O2-chain record comes first; its provisions seed the routing.
    """
    records, provisions = load_projection_layers(root)
    return _with_frozen_layer(root, records, provisions)


def _with_frozen_layer(root: Path, records: list[dict[str, Any]],
                       provisions: list[Provision]) -> tuple[list[dict[str, Any]], list[Provision]]:
    frozen_provisions = o2_chain_provisions(root)
    frozen_rows, frozen_entries = load_o2_chain_rows(root)
    chain = {"layer": O2_CHAIN_LAYER, "frozen": True, "chain": o2_chain_records(root),
             "semantic_sha256": _provisions_digest(
                 frozen_provisions, rows=[frozen_rows[name] for name in O2_CHAIN_IDENTITIES],
                 entries=[frozen_entries[name] for name in O2_CHAIN_IDENTITIES if name in frozen_entries]),
             "identities": sorted(O2_CHAIN_IDENTITIES)}
    return [chain] + records, frozen_provisions + list(provisions)


def _carrier_class_mappings(root: Path) -> dict[str, Any]:
    """Construction-only class pins without consuming the carrier outputs.

    The omitted layer provides relationships, never classes. Preserve the
    normal source, successor, duplicate and refusal rules for class mappings;
    this partial routing is not a runtime authority or coverage result.
    """
    specs = tuple(spec for spec in LAYERS + BATCH2_LAYERS
                  if spec.name != "vocabulary-carrier")
    records, provisions = _with_frozen_layer(root, *_read_projection_layers(root, specs))
    successor = generate_model_successor_contract(root, records=records, provisions=provisions)
    register = load_register_rows(root)
    routing = compute_routing(
        provisions=[p for p in provisions if p.layer != O2_CHAIN_LAYER],
        successor_contract=successor, register_rows=register,
        seed=[p for p in provisions if p.layer == O2_CHAIN_LAYER],
    )
    if routing.duplicates:
        raise ModelAuthorityRefused("duplicate providers: " + "; ".join(routing.duplicates))
    refused = set(register_refusals(register)) | set(successor.get("retired") or ()) | set(routing.retired_names)
    mappings = {}
    for name, provision in routing.providers.items():
        if provision.kind != "class":
            continue
        if name in refused:
            raise ModelAuthorityRefused(f"{name}: refused identity has a construction class provider")
        mappings[name] = provision.mapping
    if not mappings:
        raise ModelAuthorityRefused("carrier construction has no class providers")
    return mappings


def load_kernel_exclusions(root: Path = ROOT) -> tuple[str, dict[str, dict[str, str]]]:
    """Governed directory and kernel-internal declarations (D3 manifest)."""
    import yaml

    document = yaml.safe_load((Path(root) / KERNEL_INTERNAL_PATH).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ModelAuthorityRefused(f"{KERNEL_INTERNAL_PATH} must be a mapping")
    directory = document.get("governed_directory")
    declarations = document.get("declarations")
    if not isinstance(directory, str) or not directory or not isinstance(declarations, dict):
        raise ModelAuthorityRefused(f"{KERNEL_INTERNAL_PATH} lacks governed_directory/declarations")
    return directory, {str(file): {" ".join(str(d).split()): str(r) for d, r in (entries or {}).items()}
                       for file, entries in declarations.items()}


def register_refusals(register_rows: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    """Registered non-retained rows: refused with their register disposition."""
    refusals = {}
    for name, row in sorted(register_rows.items()):
        status = row.get("accounting_status")
        if status == "retained":
            continue
        disposition = str(row.get("final_disposition") or status)
        if row.get("merge_into"):
            message = (f"refused: {status} into {row['merge_into']} (register disposition "
                       f"{disposition}); no separate identity is served")
        else:
            message = (f"refused: {status} (register disposition {disposition}, "
                       f"{row.get('migration_class')}); "
                       f"{row.get('retirement_condition') or 'no successor identity'}")
        refusals[name] = message
    return refusals


# ---------------------------------------------------------------------------
# Contract construction
# ---------------------------------------------------------------------------


def _mapping_record(mapping: Any) -> dict[str, Any]:
    if isinstance(mapping, KernelFileMapping):
        return {"file": mapping.file, "declaration": mapping.declaration}
    if isinstance(mapping, KernelNativeMapping):
        return {"native": mapping.native}
    if isinstance(mapping, KernelExternalMapping):
        return {"external": mapping.external}
    raise ModelAuthorityRefused(f"unsupported class mapping {mapping!r}")


def contract_content(classes: Mapping[str, Any], relationship_mappings: Mapping[str, Any],
                     relationships: Mapping[str, Any], refused: Mapping[str, str]) -> dict[str, Any]:
    """Served meaning: exact class pins, full relationship specs/mappings, refusals.

    Relationship specs include endpoint contracts, strength/support, carrier and
    discriminator pins and serializer configuration; refusal text includes retired
    navigation and register dispositions. Build construction adds lineage pins
    and the complete successor payload (including endpoint usages and version),
    never raw layer bytes or binding provenance.
    """
    return {
        "classes": {name: _mapping_record(mapping) for name, mapping in sorted(classes.items())},
        "relationships": {name: {"spec": json.loads(json.dumps(relationships[name], sort_keys=True)),
                                 "mapping": (asdict(relationship_mappings[name])
                                             if relationship_mappings.get(name) is not None else None)}
                          for name in sorted(relationships)},
        "refused": dict(sorted(refused.items())),
    }


def lineage_pins(routing: Routing, provisions: list[Any]) -> dict[str, str]:
    """Classes served by a successor lineage pin borrowed from their unique
    specializing projected class (name -> that class)."""
    pinned: dict[str, str] = {}
    for name, provision in routing.providers.items():
        if provision.layer != "successor-contract" or provision.kind != "class":
            continue
        children = [p.identity for p in provisions if p.kind == "class" and p.identity != name
                    and isinstance(p.spec, dict) and p.spec.get("sub_class_of") == name
                    and p.mapping == provision.mapping]
        if len(children) == 1:
            pinned[name] = children[0]
    return pinned


def build_model_contract(root: Path = ROOT) -> KernelContract:
    """Build from generated meaning, not live commit bindings (fail closed).

    Identity covers served contract content, lineage pins, the full successor
    semantic payload and path-labelled declared layer semantics. Identity layer
    ``sha256`` values hash provider meaning, not file bytes: both paths of a live
    pair share its semantic digest; frozen paths share the frozen provider digest.
    Raw file receipts (including frozen source revisions) remain distinct
    provenance records. Python/pilot/unrelated model bytes and binding metadata
    never enter identity. Kernel exclusions stay a separate blocking gate.
    """
    from .relationship_successor_contract import semantic_payload

    root = Path(root)
    records, provisions = load_model_layers(root)
    chain = [p for p in provisions if p.layer == O2_CHAIN_LAYER]
    layered = [p for p in provisions if p.layer != O2_CHAIN_LAYER]
    successor = generate_model_successor_contract(root, records=records, provisions=provisions)
    register = load_register_rows(root)
    routing = compute_routing(provisions=layered, successor_contract=successor,
                                  register_rows=register, seed=chain)
    if routing.duplicates:
        raise ModelAuthorityRefused("duplicate providers: " + "; ".join(routing.duplicates))
    refused = register_refusals(register)
    for name, reason in (successor.get("retired") or {}).items():
        refused[name] = f"retired by the model successor contract: {reason}"
    for name, navigation in routing.retired_names.items():
        refused[name] = f"retired; use {navigation}"
    class_mappings: dict[str, Any] = {}
    relationship_mappings: dict[str, Any] = {}
    relationships: dict[str, Any] = {}
    retired = set(successor.get("retired") or ())
    for name, provision in sorted(routing.providers.items()):
        if name in refused:
            raise ModelAuthorityRefused(f"{name}: refused identity is also provided by {provision.layer}")
        if provision.kind == "class":
            class_mappings[name] = provision.mapping
        elif provision.kind == "relationship":
            if name in retired:
                continue
            relationships[name] = json.loads(json.dumps(provision.spec or {}))
            relationship_mappings[name] = provision.relationship
    classes = {name: {"kernel": _mapping_record(mapping)} for name, mapping in class_mappings.items()}
    lineage_pinned = lineage_pins(routing, provisions)
    directory, exclusions = load_kernel_exclusions(root)
    content = contract_content(class_mappings, relationship_mappings, relationships, refused)
    content["lineage_pinned"] = dict(sorted(lineage_pinned.items()))
    content["successor"] = semantic_payload(successor)
    layers = []
    for record in records:
        semantic_digest = record["semantic_sha256"]
        if record.get("layer") == O2_CHAIN_LAYER:
            layers.extend((item["path"], semantic_digest) for item in record["chain"])
        else:
            layers.extend(((record["projection"]["path"], semantic_digest),
                           (record["profile"]["path"], semantic_digest)))
    layers = sorted(layers)
    identity_id = "sai-" + hashlib.sha256(canonical_json(
        {"schema": SEMANTIC_AUTHORITY_SCHEMA, "layers": layers, "content": content}).encode()).hexdigest()[:32]
    identity = SemanticAuthorityIdentity(SEMANTIC_AUTHORITY_SCHEMA, identity_id, tuple(layers))
    return KernelContract(
        source=CONTRACT_SOURCE,
        identity=identity,
        governed_directory=directory,
        exclusions=exclusions,
        classes=classes,
        relationships=relationships,
        class_mappings=class_mappings,
        relationship_mappings=relationship_mappings,
        refused=refused,
        lineage_pinned=lineage_pinned,
    )


__all__ = ["build_model_contract", "contract_content", "generate_model_successor_contract",
           "load_kernel_exclusions", "load_model_layers", "model_class_pins", "o2_chain_provisions",
           "o2_chain_records", "register_refusals", "O2_CHAIN_IDENTITIES", "O2_CHAIN_LAYER"]
