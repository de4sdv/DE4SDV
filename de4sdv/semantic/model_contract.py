"""The model-built kernel contract (O4 Wave C2, design E1).

Builds the :class:`~de4sdv.semantic.kernel_contract.KernelContract` the
runtime, ingestion, validators and gates consume from model-generated sources
only:

- the live projection layers (definition batch 1 and batch 2, O2+ native and
  library rows, vocabulary carriers);
- the frozen O2-chain layer: the O2 v1-v1.2 Semantic Projection / API
  Representation Profile records (frozen O2 records, owner decision Q7) for
  the 13 identities the O3 cutover migrated. They are read-only data; their
  bytes are pinned by ``docs/method-conformance/frozen-records.json``;
- the relationship-successor contract generated from the model
  (``de4sdv_relationship_carriers.sysml``), with class pins taken from the
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

from .authority_selection import AuthoritySelectionError
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
    ("docs/method-conformance/o2/semantic-projection-v1.json", "de4sdv.semantic-projection.v1"),
    ("docs/method-conformance/o2/semantic-projection-v1.1.json", "de4sdv.semantic-projection.v1.1"),
    ("docs/method-conformance/o2/semantic-projection-v1.2.json", "de4sdv.semantic-projection.v1.2"),
)
O2_PROFILE_CHAIN = (
    ("docs/method-conformance/o2/api-representation-profile-v1.json", "de4sdv.api-representation-profile.v1"),
    ("docs/method-conformance/o2/api-representation-profile-v1.1.json", "de4sdv.api-representation-profile.v1.1"),
    ("docs/method-conformance/o2/api-representation-profile-v1.2.json", "de4sdv.api-representation-profile.v1.2"),
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

KERNEL_INTERNAL_PATH = "docs/method-conformance/o4/kernel-internal-declarations.yaml"
CONTRACT_SOURCE = "model-authority://projection-layers"





class ModelAuthorityRefused(AuthoritySelectionError):
    """The model-authority request or bundle is invalid (fail closed)."""



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
              "docs/method-conformance/o4/definition-projection.json",
              "de4sdv.o4-definition-projection/v1",
              "docs/method-conformance/o4/definition-profile.json",
              "de4sdv.o4-definition-profile/v1"),
    LayerSpec("o2plus",
              "docs/method-conformance/o2plus/semantic-projection-o2plus.json",
              "de4sdv.semantic-projection.o2plus/v1",
              "docs/method-conformance/o2plus/api-representation-profile-o2plus.json",
              "de4sdv.api-representation-profile.o2plus/v1"),
    LayerSpec("vocabulary-carrier",
              "docs/method-conformance/o4/vocabulary-carriers-projection.json",
              "de4sdv.vocabulary-carrier-projection/v1",
              "docs/method-conformance/o4/vocabulary-carriers-profile.json",
              "de4sdv.vocabulary-carrier-profile/v1"),
)

#: Definition-admission batch 2 (generator and schema owned by the admission
#: lane: ``de4sdv.o4-definition-batch2-projection/v1`` + ``-profile/v1``). It is
#: optional only while the pair is absent from the checkout; once present it
#: is bound like every other layer. Rows flow through :func:`_batch2_provider`.
BATCH2_LAYER = LayerSpec("definition-batch2",
                         "docs/method-conformance/o4/definition-batch2-projection.json",
                         "de4sdv.o4-definition-batch2-projection/v1",
                         "docs/method-conformance/o4/definition-batch2-profile.json",
                         "de4sdv.o4-definition-batch2-profile/v1",
                         required=False)
BATCH2_LAYERS: tuple[LayerSpec, ...] = (BATCH2_LAYER,)


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _canonical_digest(value: Any) -> str:
    return _sha256_bytes(canonical_json(value).encode("utf-8"))


def _read_json(root: Path, relative: str, schema: str) -> tuple[dict[str, Any], bytes]:
    path = Path(root) / relative
    try:
        raw = path.read_bytes()
        document = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise ModelAuthorityRefused(f"projection layer file unreadable: {relative}: {exc}") from exc
    if not isinstance(document, dict) or document.get("schema") != schema:
        raise ModelAuthorityRefused(f"projection layer schema mismatch: {relative}")
    return document, raw


def _row_identity(row: Mapping[str, Any]) -> str:
    identity = row.get("identity") or row.get("for_identity") or row.get("for_concept")
    if not isinstance(identity, str) or not identity or identity != identity.strip():
        raise ModelAuthorityRefused(f"projection row has a malformed identity: {identity!r}")
    return identity


@dataclass(frozen=True)
class Provision:
    """One provider's answer for one identity."""

    identity: str
    kind: str  # "class" | "relationship"
    layer: str
    mapping: Any = None  # Kernel*Mapping for classes
    spec: Any = None  # relationship spec (ontology-shaped dict)
    relationship: RelationshipMapping | None = None


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
    kind = str(row.get("semantic_kind") or "class")
    if kind != "class":
        raise ModelAuthorityRefused(
            f"{identity}: unsupported definition row semantic_kind {kind!r}")
    grounding = row.get("grounding") if isinstance(row.get("grounding"), Mapping) else {}
    return Provision(identity, "class", layer,
                     mapping=_file_mapping(grounding.get("kernel_binding_contract"), identity))


_BATCH2_CLASS_ADMISSIONS = frozenset({"definition", "external-reference"})
_BATCH2_RELATION_ADMISSIONS = frozenset({
    "relationship-vocabulary", "relationship-runtime", "external-reference",
    "successor", "retired-name"})


def _batch2_class(identity: str, row: Mapping[str, Any], layer: str) -> Provision:
    grounding = row.get("grounding") if isinstance(row.get("grounding"), Mapping) else {}
    kinds = [key for key in ("kernel_binding_contract", "kernel_native", "kernel_external")
             if grounding.get(key)]
    if len(kinds) != 1:
        raise ModelAuthorityRefused(
            f"{identity}: batch-2 class row needs exactly one kernel grounding, got {kinds}")
    value = grounding[kinds[0]]
    relations = grounding.get("ontology_relations") if isinstance(
        grounding.get("ontology_relations"), Mapping) else {}
    spec = {"sub_class_of": relations.get("sub_class_of")} if relations.get("sub_class_of") else None
    if kinds[0] == "kernel_binding_contract":
        return Provision(identity, "class", layer, mapping=_file_mapping(value, identity), spec=spec)
    if not isinstance(value, str) or value != value.strip():
        raise ModelAuthorityRefused(f"{identity}: malformed {kinds[0]} grounding")
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
    if admission == "successor":
        successor = row.get("successor") if isinstance(row.get("successor"), Mapping) else {}
        pairs = [[str(p.get("source_class") or ""), str(p.get("target_class") or "")]
                 for p in successor.get("end_pairs") or () if isinstance(p, Mapping)]
        if not pairs or not all(all(pair) for pair in pairs):
            raise ModelAuthorityRefused(f"{identity}: successor row lacks its end pairs")
        return Provision(identity, "relationship", layer,
                         spec={"end_pairs": pairs, "support": str(row.get("support") or "")})
    relation = row.get("relation")
    if not isinstance(relation, Mapping):
        raise ModelAuthorityRefused(f"{identity}: relationship row lacks a relation declaration")
    domain = str((relation.get("domain") or {}).get("ontology_class") or "")
    range_record = relation.get("range") or {}
    range_ = str(range_record.get("ontology_class") or "")
    if not domain or not range_:
        raise ModelAuthorityRefused(f"{identity}: incomplete relationship domain/range")
    strength = relation.get("semantic_strength")
    if admission == "retired-name":
        retired = row.get("retired") if isinstance(row.get("retired"), Mapping) else {}
        resolution = (entry or {}).get("retired_resolution") or {}
        spec = {"successor": retired.get("successor"),
                "navigation": retired.get("successor_navigation"),
                "refusal": retired.get("refusal"),
                "profile_successor": resolution.get("successor"),
                "profile_navigation": resolution.get("navigation")}
        return Provision(identity, "retired", layer, spec=spec)
    spec: dict[str, Any] = {"domain": domain, "range": range_,
                            "support": str(row.get("support") or "vocabulary-only")}
    if strength is not None:
        spec["semantic_strength"] = str(strength)
    discriminator = _batch2_discriminator(identity, range_record)
    if discriminator is not None:
        spec["range_discriminator"] = discriminator
    carrier = row.get("carrier")
    if carrier is not None:
        pinned = _file_mapping(carrier, identity)
        spec["carrier"] = {"file": pinned.file, "declaration": pinned.declaration}
    mechanics = dict((entry or {}).get("serializer_mechanics") or {})
    strategy = str(mechanics.pop("strategy", "") or "")
    if not strategy:
        return Provision(identity, "relationship", layer, spec=spec)
    if not strength:
        raise ModelAuthorityRefused(f"{identity}: serialized relationship lacks a semantic strength")
    mapping = RelationshipMapping(name=identity, strategy=strategy, semantic_strength=str(strength),
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
    kind = row.get("semantic_kind")
    admission = row.get("admission_class")
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
    category = str(row.get("category") or "")
    construct = str(row.get("construct") or "")
    if not construct:
        raise ModelAuthorityRefused(f"{identity}: O2+ row lacks its construct")
    if identity in _RELATIONSHIP_O2P or row.get("semantic_kind") == "relationship":
        spec = {"support": str(row.get("support") or "vocabulary-only"), "construct": construct}
        return Provision(identity, "relationship", layer, spec=spec)
    if category == "native":
        return Provision(identity, "class", layer, mapping=KernelNativeMapping(construct))
    if category == "library-mapped-native":
        return Provision(identity, "class", layer, mapping=KernelExternalMapping(construct))
    if category == "model-resident-vocabulary":
        witness = (row.get("grounding") or {}).get("witness") or {}
        contains = str(witness.get("contains") or "").strip()
        if contains.endswith("{"):
            contains = contains[:-1].strip()
        return Provision(identity, "class", layer,
                         mapping=_file_mapping({"file": witness.get("file"),
                                                "declaration": contains}, identity))
    raise ModelAuthorityRefused(f"{identity}: unsupported O2+ category {category!r}")


def _carrier_provider(row: Mapping[str, Any], layer: str) -> Provision:
    identity = _row_identity(row)
    domain = (row.get("domain") or {}).get("identity")
    range_ = (row.get("range") or {}).get("identity")
    carrier = _file_mapping(row.get("carrier"), identity)
    if not domain or not range_:
        raise ModelAuthorityRefused(f"{identity}: carrier row lacks domain/range")
    spec = {"domain": str(domain), "range": str(range_),
            "carrier": {"file": carrier.file, "declaration": carrier.declaration},
            "support": str(row.get("support") or "vocabulary-only")}
    return Provision(identity, "relationship", layer, spec=spec)


def _layer_provisions(spec: LayerSpec, projection: dict[str, Any],
                      profile: dict[str, Any]) -> list[Provision]:
    entries = {}
    for entry in profile.get("entries") or ():
        entries[_row_identity(entry)] = entry
    rows = projection.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ModelAuthorityRefused(f"{spec.name}: projection has no rows")
    result = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ModelAuthorityRefused(f"{spec.name}: malformed projection row")
        identity = _row_identity(row)
        if spec.name == "o2plus":
            result.append(_o2plus_provider(row, spec.name))
        elif spec.name == "vocabulary-carrier":
            result.append(_carrier_provider(row, spec.name))
        elif spec.name == BATCH2_LAYER.name:
            result.append(_batch2_provider(row, entries.get(identity), spec.name))
        else:
            result.append(_definition_row_provider(row, entries.get(identity), spec.name))
    return result


def load_projection_layers(root: Path = ROOT) -> tuple[list[dict[str, Any]], list[Provision]]:
    """Read every live projection layer: (bundle records, provisions)."""
    records: list[dict[str, Any]] = []
    provisions: list[Provision] = []
    for spec in LAYERS + BATCH2_LAYERS:
        if not spec.required and not (Path(root) / spec.projection_path).exists():
            continue
        projection, projection_raw = _read_json(root, spec.projection_path, spec.projection_schema)
        profile, profile_raw = _read_json(root, spec.profile_path, spec.profile_schema)
        layer_provisions = _layer_provisions(spec, projection, profile)
        records.append({
            "layer": spec.name,
            "projection": {"path": spec.projection_path, "schema": spec.projection_schema,
                           "sha256": _sha256_bytes(projection_raw),
                           "source_revision": (projection.get("binding") or {}).get("source_revision")},
            "profile": {"path": spec.profile_path, "schema": spec.profile_schema,
                        "sha256": _sha256_bytes(profile_raw),
                        "source_revision": (profile.get("binding") or {}).get("source_revision")},
            "identities": sorted(p.identity for p in layer_provisions),
        })
        provisions.extend(layer_provisions)
    return records, provisions


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
    gate and bundle construction refuse a non-empty residual).
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
    path = Path(root) / "docs/method-conformance/o4/o4-execution-register.json"
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
    chain = {"layer": O2_CHAIN_LAYER, "frozen": True, "chain": o2_chain_records(root),
             "identities": sorted(O2_CHAIN_IDENTITIES)}
    return [chain] + records, o2_chain_provisions(root) + list(provisions)


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
    """Canonical semantic content of a contract (identity digest input)."""
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
    """Build the kernel contract from the model-generated layers (fail closed)."""
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
    layers = []
    for record in records:
        if record.get("layer") == O2_CHAIN_LAYER:
            layers.extend((item["path"], item["sha256"]) for item in record["chain"])
        else:
            layers.extend(((record["projection"]["path"], record["projection"]["sha256"]),
                           (record["profile"]["path"], record["profile"]["sha256"])))
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
