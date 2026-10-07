"""O4 Wave B model-authority runtime: one closed ``mab-`` bundle, fail closed.

The model-authority bundle (``de4sdv.model-authority-bundle/v1``) is a
deployment input. It binds, under one content digest:

- the closed O3 component (embedded document, recomputed id and digest);
- every model projection layer as a projection/profile pair (path, schema,
  sha256, source revision): definitions (batch 1 plus the batch-2 rows when
  present), O2+ native/library rows and vocabulary carriers;
- the relationship-successor contract generated from the model at bundle
  construction (``relationship_successor_contract.generate_contract``) and
  regenerated and compared again at runtime construction;
- the executed implementation manifest (the sidecar sources this path runs
  that are not frozen O3 runtime-build inputs);
- the routing table: exactly one provider per identity, plus the explicit,
  owner-visible residual that still uses the authored ontology YAML;
- after closure, a structured attestation (binding, validation evidence and
  recomputed activation eligibility).

Selection is explicit (``DE4SDV_SEMANTIC_AUTHORITY=model`` with
``DE4SDV_MODEL_AUTHORITY_BUNDLE`` and ``DE4SDV_MODEL_AUTHORITY_BUNDLE_ID``) and
is routed by :func:`de4sdv.semantic.composition_construction.build_explicit_semantic_runtime`.
The frozen ``authority_selection`` module (an O3 runtime-build input) is not
changed: legacy and o3 selection stay byte-identical and remain the rollback
path. A failed model request never degrades to o3 or legacy.

Successor exposure follows the owner decision of 2026-10-07: ``allocatedTo``,
``hasValidationScenario`` (inverse ``validationScenarioFor``) and
``hasRegulatorySource`` are served from the model-derived successor
contract. The retired names stay answerable ONLY through the documented
deprecated-alias table :data:`DEPRECATED_ALIASES`; every alias edge and every
alias-bearing result carries a ``deprecated_alias`` marker. Aliases are never
part of the default predicate set and are deleted in Wave C.

``hasRelevantEvidenceContract`` uses the owner-adopted discriminator: its
range is the authored type closure of the validated ``EvidenceContract``
kernel root, which must contain exactly :data:`EXPECTED_EVIDENCE_CONTRACT_DEFINITIONS`
specializing definitions (the eight AEBS evidence contracts). Any other
population fails closed with :data:`MODEL_EVIDENCE_CONTRACT_BLOCKED_REASON`.
``traversal.py`` is untouched; the discriminator is a subclass override.

Non-claims: constructing or closing a bundle is not production activation,
consumer retirement, compliance or a semantic proof beyond the bound
artifacts. Production activation stays owner-gated.
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

from .kernel_contract import (
    KernelContract,
    KernelExternalMapping,
    KernelFileMapping,
    KernelNativeMapping,
    RelationshipMapping,
    declaration_identity,
)
from .o3_bundle import (
    MIGRATED_CLASSES,
    MIGRATED_IDENTITIES,
    MIGRATED_RELATIONSHIPS,
    O3_BUNDLE_SCHEMA,
    O3ImpactService,
    PROFILE_CHAIN,
    PROJECTION_CHAIN,
    candidate_provenance,
    canonical_json,
)
from .authority_selection import AuthoritySelectionError
from .relationship_successor import SuccessorQueryService, SuccessorTraversal

ROOT = Path(__file__).resolve().parents[2]

MODEL_AUTHORITY = "model"
AUTHORITY_ENV = "DE4SDV_SEMANTIC_AUTHORITY"
MODEL_BUNDLE_PATH_ENV = "DE4SDV_MODEL_AUTHORITY_BUNDLE"
MODEL_BUNDLE_ID_ENV = "DE4SDV_MODEL_AUTHORITY_BUNDLE_ID"

MODEL_BUNDLE_SCHEMA = "de4sdv.model-authority-bundle/v1"
MODEL_ATTESTATION_SCHEMA = "de4sdv.model-authority-closure/v1"
ROUTING_SCHEMA = "de4sdv.model-authority-routing/v1"
IMPLEMENTATION_SCHEMA = "de4sdv.model-authority-implementation/v1"
BUNDLE_ID_RE = re.compile(r"^mab-[0-9a-f]{32}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")

#: Activation-gating validation evidence (each exactly ``passed`` + digest).
#: The requirement-population delta is measured evidence, not a gate.
REQUIRED_MODEL_VALIDATIONS = (
    "model_projection_coverage",
    "model_o3_legacy_equivalence",
    "verification_anchor_readback",
)

#: Owner decision 5 (2026-10-07): the EvidenceContract type closure is exactly
#: the eight AEBS evidence-contract definitions.
EXPECTED_EVIDENCE_CONTRACT_DEFINITIONS = 8
EVIDENCE_CONTRACT_CLASS = "EvidenceContract"
DISCRIMINATED_PREDICATES = ("hasRelevantEvidenceContract",)
MODEL_EVIDENCE_CONTRACT_BLOCKED_REASON = (
    "EvidenceContract type closure is not established at this revision: the "
    "model-authority discriminator requires the validated EvidenceContract "
    "kernel root and exactly "
    f"{EXPECTED_EVIDENCE_CONTRACT_DEFINITIONS} authored specializing "
    "requirement definitions; native verification membership alone never "
    "establishes the range."
)


@dataclass(frozen=True)
class DeprecatedAlias:
    """One documented deprecated alias (owner decision 3, 2026-10-07)."""

    successor: str
    end_pair: tuple[str, str] | None
    claim_boundary: str
    #: ``successor-facts``: answers are the successor's facts (restricted to
    #: ``end_pair``); ``documentation-only``: the model retirement record
    #: refuses an alias reading, so the name answers no facts and points to
    #: the successor.
    answer_mode: str = "successor-facts"
    #: Navigation name over the successor relation (its inverse for an
    #: inverse alias); defaults to the successor itself.
    navigation: str | None = None

    @property
    def navigated(self) -> str:
        return self.navigation or self.successor


#: The ONLY retired names still answerable. Each answers through the named
#: successor (restricted to one approved end pair where the retired name was
#: narrower) and never with a stronger meaning than the successor contract.
DEPRECATED_ALIASES: Mapping[str, DeprecatedAlias] = MappingProxyType({
    "realizedBy": DeprecatedAlias(
        "allocatedTo", ("Requirement", "Function"),
        "responsibility assignment only; no realization, satisfaction or fulfillment"),
    "deployedTo": DeprecatedAlias(
        "allocatedTo", ("LogicalElement", "PhysicalElement"),
        "responsibility assignment only; no software deployment or observed operation"),
    "validatedBy": DeprecatedAlias(
        "hasValidationScenario", None,
        "validation planning association only; no validation result or acceptance"),
    "validatesFitnessForUse": DeprecatedAlias(
        "hasValidationScenario", None,
        "inverse planning navigation only; no fitness-for-use verdict",
        navigation="validationScenarioFor"),
    "constrainedBy": DeprecatedAlias(
        "hasRegulatorySource", None,
        "historical source provenance, not native required conditions; the "
        "controlled-source successor is hasRegulatorySource, not an alias: no "
        "fact is answered under this name",
        answer_mode="documentation-only"),
})
ALIAS_REMOVAL = "Wave C deletes the deprecated aliases"


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
    "successor", "deprecated-alias"})


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
    if admission == "deprecated-alias":
        alias = row.get("alias") if isinstance(row.get("alias"), Mapping) else {}
        resolution = (entry or {}).get("alias_resolution") or {}
        spec = {"successor": alias.get("successor"), "answer_mode": alias.get("answer_mode"),
                "navigation": alias.get("successor_navigation"),
                "profile_successor": resolution.get("successor"),
                "profile_navigation": resolution.get("navigation"),
                "profile_answer_mode": resolution.get("answer_mode"),
                "deprecated": alias.get("deprecated")}
        return Provision(identity, "alias", layer, spec=spec)
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


def load_layers(root: Path = ROOT) -> tuple[list[dict[str, Any]], list[Provision]]:
    """Read every projection layer: (bundle records, provisions)."""
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


def o3_chain_records(root: Path = ROOT) -> list[dict[str, str]]:
    records = []
    for relative, schema in PROJECTION_CHAIN + PROFILE_CHAIN:
        records.append({"path": relative, "schema": schema,
                        "sha256": _sha256_bytes((Path(root) / relative).read_bytes())})
    return records


# ---------------------------------------------------------------------------
# Successor contract + routing
# ---------------------------------------------------------------------------


def generate_successor_contract(root: Path = ROOT) -> dict[str, Any]:
    """Generate the successor contract from the model (never from YAML decisions)."""
    from .relationship_successor_contract import generate_contract, verify_contract

    contract = generate_contract(Path(root))
    verify_contract(contract, Path(root))
    return contract


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

    def record(self) -> dict[str, Any]:
        return {
            "schema": ROUTING_SCHEMA,
            "providers": {name: p.layer for name, p in sorted(self.providers.items())},
            "corroborations": {k: list(v) for k, v in sorted(self.corroborations.items())},
            "duplicates": list(self.duplicates),
            "residual": dict(sorted(self.residual.items())),
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


def _alias_disagreement(provision: Provision) -> str | None:
    """A batch-2 deprecated-alias row must document exactly the alias table."""
    alias = DEPRECATED_ALIASES.get(provision.identity)
    spec = provision.spec or {}
    if alias is None:
        return "not in the documented deprecated-alias table"
    expected = {"successor": alias.successor, "profile_successor": alias.successor,
                "navigation": alias.navigated, "profile_navigation": alias.navigated,
                "answer_mode": alias.answer_mode, "profile_answer_mode": alias.answer_mode,
                "deprecated": True}
    differing = sorted(k for k, v in expected.items() if spec.get(k) != v)
    return f"differs from the documented alias table in {differing}" if differing else None


def _authored_disagreement(legacy: KernelContract, provision: Provision) -> str | None:
    """While the authored YAML still exists, a batch-2 row must equal it."""
    name = provision.identity
    if provision.kind == "class":
        if name in legacy.classes and legacy.mapping(name) != provision.mapping:
            return "mapping differs from the authored ontology"
        return None
    authored = legacy.relationships.get(name)
    if not isinstance(authored, Mapping):
        return None
    spec = provision.spec or {}
    if "domain" in spec and (authored.get("domain"), authored.get("range")) != (
            spec["domain"], spec["range"]):
        return "domain/range differs from the authored ontology"
    try:
        authored_mapping = legacy.relationship_mapping(name)
    except KeyError:
        authored_mapping = None
    if provision.relationship != authored_mapping:
        return "SysML mapping differs from the authored ontology"
    return None


def compute_routing(*, legacy: KernelContract, provisions: list[Provision],
                    successor_contract: Mapping[str, Any],
                    register_rows: Mapping[str, Mapping[str, Any]] | None = None) -> Routing:
    """Disjoint provider routing; duplicates are recorded (and refused by callers)."""
    providers: dict[str, Provision] = {}
    corroborations: dict[str, list[str]] = {}
    duplicates: list[str] = []
    for name in MIGRATED_IDENTITIES:
        kind = "class" if name in MIGRATED_CLASSES else "relationship"
        providers[name] = Provision(name, kind, "o3")
    retired = set(DEPRECATED_ALIASES) | set(successor_contract.get("retired") or ())
    ordered = list(provisions)
    for successor in _successor_provisions(successor_contract):
        existing = providers.get(successor.identity)
        if existing is not None and existing.layer != "o3" and _corroborates(
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
        if provision.kind == "alias":
            problem = _alias_disagreement(provision)
            if problem:
                duplicates.append(f"{name}: {provision.layer} deprecated alias {problem}")
            else:
                corroborations.setdefault(name, []).append(provision.layer)
            continue
        if name in retired:
            duplicates.append(f"{name}: retired name provided by {provision.layer}")
            continue
        if provision.layer == BATCH2_LAYER.name and provision.kind != "relationship" or (
                provision.layer == BATCH2_LAYER.name and "end_pairs" not in (provision.spec or {})):
            problem = _authored_disagreement(legacy, provision)
            if problem:
                duplicates.append(f"{name}: {provision.layer} {problem}")
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
        if existing.layer != "o3" and _corroborates(existing, provision, successor_contract):
            if provision.layer == "successor-contract" and provision.kind == "relationship":
                providers[name] = provision
                corroborations.setdefault(name, []).append(existing.layer)
            else:
                corroborations.setdefault(name, []).append(provision.layer)
            continue
        duplicates.append(f"{name}: {existing.layer} and {provision.layer}")
    residual: dict[str, str] = {}
    universe = set(legacy.classes) | set(legacy.relationships)
    if register_rows:
        universe |= {n for n, r in register_rows.items() if r.get("accounting_status") == "retained"}
    for name in sorted(universe):
        if name in providers or name in retired:
            continue
        row = (register_rows or {}).get(name)
        if row is None:
            reason = ("unregistered ontology YAML identity: no model projection "
                      "layer provides it; the authored YAML entry is its source")
        else:
            reason = ("no model projection layer provides this retained row; the "
                      "authored YAML entry is its source (migration_class="
                      f"{row.get('migration_class')}, final_disposition="
                      f"{row.get('final_disposition')})")
        residual[name] = reason
    return Routing(MappingProxyType(providers),
                   MappingProxyType({k: tuple(v) for k, v in corroborations.items()}),
                   tuple(sorted(duplicates)), MappingProxyType(residual))


def load_register_rows(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    path = Path(root) / "docs/method-conformance/o4/o4-execution-register.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    return {row["identity"]: row for row in document["rows"]}


# ---------------------------------------------------------------------------
# Implementation manifest
# ---------------------------------------------------------------------------

#: Executed sidecar sources of the model path that are NOT frozen O3
#: runtime-build inputs (those stay covered by the embedded O3 bundle).
IMPLEMENTATION_FILES = (
    "de4sdv/semantic/model_authority_runtime.py",
    "de4sdv/semantic/composition_construction.py",
    "de4sdv/semantic/relationship_successor.py",
    "de4sdv/semantic/relationship_successor_contract.py",
    "de4sdv/semantic/definition_candidate.py",
    "de4sdv/semantic/definition_candidate_provider.py",
    "de4sdv/semantic/definition_migration.py",
    "de4sdv/semantic/model_edges.py",
    "de4sdv/semantic/relationships.py",
    "de4sdv/sysml_api/client.py",
    "de4sdv/sysml_api/repository.py",
)


def _executed_sources() -> dict[str, str | None]:
    from de4sdv.sysml_api import client, repository
    from . import (composition_construction, definition_candidate, definition_candidate_provider,
                   definition_migration, model_edges, relationship_successor,
                   relationship_successor_contract, relationships)

    modules = (sys.modules[__name__], composition_construction, relationship_successor,
               relationship_successor_contract, definition_candidate,
               definition_candidate_provider, definition_migration, model_edges,
               relationships, client, repository)
    return {rel: inspect.getsourcefile(module) for rel, module in zip(IMPLEMENTATION_FILES, modules)}


def implementation_manifest(root: Path = ROOT) -> dict[str, Any]:
    """Bind executed sidecar bytes; refuse substituted (external) sources."""
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

_ID_COMPONENTS = ("schema", "git_revision", "ontology_compatibility_identity", "components")


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
            "deprecated_aliases": {name: {"successor": a.successor,
                                          "end_pair": list(a.end_pair) if a.end_pair else None,
                                          "navigation": a.navigated,
                                          "answer_mode": a.answer_mode,
                                          "claim_boundary": a.claim_boundary}
                                   for name, a in sorted(DEPRECATED_ALIASES.items())}}


def model_components(root: Path = ROOT, *, o3_bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Everything the bundle id binds, recomputed from the checkout."""
    if not isinstance(o3_bundle, Mapping) or o3_bundle.get("schema") != O3_BUNDLE_SCHEMA:
        raise ModelAuthorityRefused("model bundle requires an O3 bundle document")
    legacy = KernelContract.load(Path(root) / "approach/framework/ontology/de4sdv-basic-ontology.yaml")
    records, provisions = load_layers(root)
    contract = generate_successor_contract(root)
    routing = compute_routing(legacy=legacy, provisions=provisions, successor_contract=contract,
                              register_rows=load_register_rows(root))
    o3_document = json.loads(json.dumps(dict(o3_bundle)))
    return {
        "o3": {"bundle_id": str(o3_bundle.get("bundle_id") or ""),
               "sha256": _canonical_digest(o3_document),
               "state": o3_bundle.get("state"),
               "chain": o3_chain_records(root),
               "document": o3_document},
        "layers": records,
        "successor_contract": _successor_record(contract),
        "routing": routing.record(),
        "implementation_manifest": implementation_manifest(root),
    }


def build_model_bundle(root: Path = ROOT, *, o3_bundle: Mapping[str, Any],
                       git_revision: str) -> dict[str, Any]:
    """Construct a candidate (unclosed) model-authority bundle."""
    if not _REVISION_RE.fullmatch(str(git_revision or "")):
        raise ModelAuthorityRefused("git_revision must be a full 40-hex commit id")
    if o3_bundle.get("git_revision") != git_revision:
        raise ModelAuthorityRefused("O3 component is bound to a different Git revision")
    components = model_components(root, o3_bundle=o3_bundle)
    if components["routing"]["duplicates"]:
        raise ModelAuthorityRefused("duplicate providers: " + "; ".join(components["routing"]["duplicates"]))
    ontology = Path(root) / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
    bundle = {
        "schema": MODEL_BUNDLE_SCHEMA,
        "git_revision": git_revision,
        "ontology_compatibility_identity": {
            "path": "approach/framework/ontology/de4sdv-basic-ontology.yaml",
            "sha256": hashlib.sha256(ontology.read_bytes()).hexdigest()},
        "components": components,
        "state": "candidate",
        "claim_boundary": ("deployment input; closure is not activation, consumer "
                           "retirement, compliance or certification"),
    }
    bundle["bundle_id"] = compute_model_bundle_id(bundle)
    return bundle


def _eligibility(attestation: Mapping[str, Any]) -> bool:
    validation = attestation.get("validation")
    return (attestation.get("o3_activation_eligible") is True
            and attestation.get("definition_closure_closed") is True
            and isinstance(validation, Mapping)
            and set(validation) == set(REQUIRED_MODEL_VALIDATIONS)
            and all(isinstance(r, Mapping) and r.get("status") == "passed"
                    and _DIGEST_RE.fullmatch(str(r.get("sha256") or ""))
                    for r in validation.values()))


def build_model_closure_attestation(bundle: Mapping[str, Any], *, binding: Any,
                                    binding_sha256: str, definition_closure_closed: bool,
                                    validations: Mapping[str, Mapping[str, Any]],
                                    generated_at: str) -> dict[str, Any]:
    o3_closure = (bundle["components"]["o3"]["document"].get("api_closure") or {})
    attestation = {
        "schema": MODEL_ATTESTATION_SCHEMA,
        "bundle_id": bundle["bundle_id"],
        "git_revision": bundle["git_revision"],
        "binding_sha256": binding_sha256,
        "sysml_project_id": str(binding.sysml_project_id),
        "sysml_commit_id": str(binding.sysml_commit_id),
        "o3_activation_eligible": o3_closure.get("activation_eligible") is True,
        "definition_closure_closed": bool(definition_closure_closed),
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
        return ["model bundle schema mismatch"]
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
    o3 = components.get("o3") or {}
    document = o3.get("document")
    if not isinstance(document, Mapping) or document.get("bundle_id") != o3.get("bundle_id"):
        errors.append("O3 component id does not equal its embedded document")
        document = {}
    else:
        try:
            expected = model_components(root, o3_bundle=document)
        except Exception as exc:  # recomputation failures are verification failures
            return errors + [f"model components cannot be recomputed: {exc}"]
        for key in ("o3", "layers", "successor_contract", "routing", "implementation_manifest"):
            if components.get(key) != expected[key]:
                errors.append(f"model bundle component {key!r} differs from the checkout")
        if set(components) != set(expected):
            errors.append("model bundle component set differs")
        if expected["routing"]["duplicates"]:
            errors.append("duplicate providers: " + "; ".join(expected["routing"]["duplicates"]))
    if document and document.get("git_revision") != bundle.get("git_revision"):
        errors.append("O3 component is bound to a different Git revision")
    ontology = Path(root) / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
    record = bundle.get("ontology_compatibility_identity") or {}
    if record.get("sha256") != hashlib.sha256(ontology.read_bytes()).hexdigest():
        errors.append("ontology compatibility identity digest mismatch")
    if require_closed and state != "closed":
        errors.append("model bundle is not closed: production selection requires the closure attestation")
    if state == "closed":
        closure = bundle.get("closure")
        if not isinstance(closure, Mapping):
            errors.append("closed model bundle carries no closure attestation")
        else:
            errors.extend(_closure_errors(bundle, closure, binding=binding,
                                          binding_sha256=binding_sha256,
                                          validation_artifacts=validation_artifacts))
    return errors


def _closure_errors(bundle, closure, *, binding, binding_sha256, validation_artifacts):
    errors = []
    if closure.get("schema") != MODEL_ATTESTATION_SCHEMA:
        errors.append("model closure attestation schema mismatch")
    if closure.get("bundle_id") != bundle.get("bundle_id"):
        errors.append("closure attestation is bound to a different bundle id")
    if closure.get("git_revision") != bundle.get("git_revision"):
        errors.append("closure attestation git revision mismatch")
    if closure.get("activation_eligible") is not _eligibility(closure):
        errors.append("recorded activation_eligible differs from the recomputed value")
    o3_closure = (bundle["components"]["o3"].get("document") or {}).get("api_closure") or {}
    if closure.get("o3_activation_eligible") is not (o3_closure.get("activation_eligible") is True):
        errors.append("closure o3_activation_eligible differs from the O3 component")
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
    return errors


# ---------------------------------------------------------------------------
# Runtime facade (duck-compatible with KernelContract / O3AuthorityFacade)
# ---------------------------------------------------------------------------


class ModelAuthorityFacade:
    """One disjoint routing table; residual identities are explicit legacy."""

    def __init__(self, *, legacy: KernelContract, o3_facade: Any, routing: Routing,
                 successor_contract: Mapping[str, Any], bundle_id: str,
                 components: Mapping[str, Any]) -> None:
        if routing.duplicates:
            raise ModelAuthorityRefused("duplicate providers: " + "; ".join(routing.duplicates))
        if o3_facade.identity != legacy.identity:
            raise ModelAuthorityRefused("component ontology identity conflict")
        self._legacy = legacy
        self._o3 = o3_facade
        self._routing = routing
        self._components = components
        self.profile = json.loads(json.dumps(dict(successor_contract)))
        self._inverse = {}
        for name, rows in self.profile["relations"].items():
            if rows[0].get("inverse"):
                self._inverse[rows[0]["inverse"]] = name
        self.identity = legacy.identity
        self.source = legacy.source
        self.bundle_id = bundle_id
        self.authority_id = model_authority_id(bundle_id)
        self.binding_routes: list[dict[str, Any]] = []
        self.residual_identities = tuple(sorted(routing.residual))
        self.classes = self._merged_classes()
        self.relationships = self._merged_relationships()

    def provider_of(self, name: str) -> str:
        provision = self._routing.providers.get(name)
        if provision is not None:
            return provision.layer
        if name in DEPRECATED_ALIASES:
            return "deprecated-alias"
        return "residual-authored-yaml"

    def _merged_classes(self) -> dict[str, Any]:
        merged = {}
        for name in set(self._legacy.classes) | {
                n for n, p in self._routing.providers.items() if p.kind == "class"}:
            if name in self._routing.providers and self._routing.providers[name].kind == "class":
                mapping = self.mapping(name)
                if isinstance(mapping, KernelFileMapping):
                    merged[name] = {"kernel": {"file": mapping.file, "declaration": mapping.declaration}}
                elif isinstance(mapping, KernelNativeMapping):
                    merged[name] = {"kernel": {"native": mapping.native}}
                else:
                    merged[name] = {"kernel": {"external": mapping.external}}
            else:
                merged[name] = self._legacy.classes[name]
        return merged

    def _merged_relationships(self) -> dict[str, Any]:
        merged = {}
        names = set(self._legacy.relationships) | {
            n for n, p in self._routing.providers.items() if p.kind == "relationship"}
        retired = set(DEPRECATED_ALIASES) | set(self.profile.get("retired") or ())
        for name in names:
            if name in retired:
                continue  # answerable only as a documented deprecated alias
            provision = self._routing.providers.get(name)
            if provision is None:
                merged[name] = self._legacy.relationships[name]
            elif provision.layer == "o3":
                merged[name] = self._o3.relationships[name]
            else:
                merged[name] = provision.spec
        return merged

    def mapping(self, name: str) -> Any:
        provision = self._routing.providers.get(name)
        if provision is None or provision.kind != "class":
            return self._legacy.mapping(name)
        if provision.layer == "o3":
            return self._o3.mapping(name)
        return provision.mapping

    def class_mapping(self, name: str) -> KernelFileMapping:
        mapping = self.mapping(name)
        if not isinstance(mapping, KernelFileMapping):
            raise ValueError(f"ontology class {name} is not file-mapped")
        return mapping

    def relationship_mapping(self, name: str) -> RelationshipMapping:
        alias = DEPRECATED_ALIASES.get(name)
        if alias is not None:
            target = self.relationship_mapping(alias.navigated)
            domain, range_ = alias.end_pair or (target.domain, target.range)
            return RelationshipMapping(name, "deprecated-alias", target.semantic_strength,
                                       {"successor": alias.successor}, domain, range_)
        provision = self._routing.providers.get(name)
        if provision is None:
            return self._legacy.relationship_mapping(name)
        if provision.layer == "o3":
            return self._o3.relationship_mapping(name)
        if provision.relationship is None:
            raise KeyError(f"ontology relationship has no SysML mapping: {name}")
        return provision.relationship

    def provenance(self) -> dict[str, Any]:
        layers = [{"layer": r["layer"], "projection_sha256": r["projection"]["sha256"],
                   "profile_sha256": r["profile"]["sha256"]} for r in self._components["layers"]]
        return {
            "kind": MODEL_AUTHORITY,
            "authority_id": self.authority_id,
            "bundle_id": self.bundle_id,
            "o3_bundle_id": self._components["o3"]["bundle_id"],
            "layers": layers,
            "successor_contract_id": self._components["successor_contract"]["id"],
            "implementation_manifest_id": self._components["implementation_manifest"]["id"],
            "residual_identities": list(self.residual_identities),
            "deprecated_aliases": sorted(DEPRECATED_ALIASES),
            "binding_routes": list(self.binding_routes),
            "status": "model authority; production activation is owner-gated",
        }


# ---------------------------------------------------------------------------
# Traversal / query / impact (provenance via subclassing)
# ---------------------------------------------------------------------------


def alias_marker(name: str) -> dict[str, Any]:
    alias = DEPRECATED_ALIASES[name]
    return {"alias": name, "successor": alias.successor, "navigation": alias.navigated,
            "end_pair": list(alias.end_pair) if alias.end_pair else None,
            "claim_boundary": alias.claim_boundary, "answer_mode": alias.answer_mode,
            "deprecated": True, "removal": ALIAS_REMOVAL}


class ModelAuthorityTraversal(SuccessorTraversal):
    """Successor traversal + deprecated aliases + EvidenceContract discriminator."""

    def __init__(self, contract, kernel_bindings):
        super().__init__(contract, kernel_bindings)
        self.aliases_used: list[str] = []

    def blocked_predicates(self) -> frozenset[str]:
        return frozenset(super().blocked_predicates()) - set(DISCRIMINATED_PREDICATES)

    def traverse(self, predicate, source, elements):
        alias = DEPRECATED_ALIASES.get(predicate)
        if alias is None:
            return super().traverse(predicate, source, elements)
        if predicate not in self.aliases_used:
            self.aliases_used.append(predicate)
        if alias.answer_mode == "documentation-only":
            reason = (self.contract.profile.get("retired") or {}).get(predicate) or alias.claim_boundary
            self.unavailable(predicate, reason, "retired")
            return []
        canonical = self.contract._inverse.get(alias.navigated, alias.navigated)
        rows = list(self.contract.profile["relations"][canonical])
        if alias.end_pair is not None:
            rows = [r for r in rows if (r["sourceClass"], r["targetClass"]) == alias.end_pair]
            if len(rows) != 1:
                self.unavailable(predicate, "deprecated alias end pair is not in the successor contract")
                return []
        # _successor_hops reads "requested != canonical" as inverse navigation,
        # so it receives the alias's navigation name; hops are relabelled afterwards.
        before = len(self.unsupported)
        try:
            hops = self._successor_hops(alias.navigated, canonical, rows, source, elements)
        except IdentityNotFoundError as exc:
            self.unavailable(predicate, exc)
            return []
        for record in self.unsupported[before:]:
            record["predicate"] = predicate
        marker = alias_marker(predicate)
        return [replace(h, predicate=predicate,
                        witness={**h.witness, "deprecated_alias": marker}) for h in hops]

    def _evidence_contract_identity_ids(self, elements):
        """Owner-adopted discriminator: the EvidenceContract type closure.

        Root identity comes from the ingestion-validated kernel binding; the
        closure follows AUTHORED subsumption only. It must contain exactly
        the expected number of specializing requirement definitions; members
        are the usages explicitly typed by the root or one of them.
        """
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
        types = definitions | {root_id}
        return {element for element, typed in resolver["typed_by"].items()
                if element not in closure and set(typed) & types}


def _component_provenance(contract) -> list[dict[str, str]]:
    components = contract._components
    entries = [{"authority": "semantic-authority", "source": f"model-authority://{contract.authority_id}"},
               {"authority": "semantic-authority",
                "source": f"projection://o3:{components['o3']['bundle_id']}"}]
    for record in components["layers"]:
        entries.append({"authority": "semantic-authority",
                        "source": f"projection-layer://{record['layer']}",
                        "sha256": record["projection"]["sha256"]})
    entries.append({"authority": "semantic-authority",
                    "source": f"successor-contract://{components['successor_contract']['id']}"})
    entries.append({"authority": "runtime-implementation",
                    "source": f"implementation://{components['implementation_manifest']['id']}"})
    if contract.residual_identities:
        entries.append({"authority": "residual-authored-fallback",
                        "source": f"{contract.source} ({len(contract.residual_identities)} identities)"})
    return entries


class ModelAuthorityQueryService(SuccessorQueryService):
    def _provenance(self):
        return super()._provenance() + _component_provenance(self.contract)

    def _semantic_authority(self):
        return {"id": self.semantic_authority_id, "kind": MODEL_AUTHORITY,
                "bundle_id": self.contract.bundle_id,
                "residual_count": len(self.contract.residual_identities),
                "note": ("explicitly selected model-authority bundle; projected identities "
                         "resolve through their verified layer, the listed residual through "
                         "the authored YAML; deprecated aliases are marked in results")}

    #: Set by :func:`build_model_authority_runtime` to the verified selection.
    selection: "ModelAuthoritySelection | None" = None

    def authority_status(self) -> dict[str, Any]:
        """Entry-point identity contract (``authority``/``bundle_id``/
        ``source_revision``/``residual``/``rollback``).

        ``residual`` lists the identities still served by the authored YAML
        (an explicit, owner-visible exception, never a silent fallback);
        ``rollback`` names the tested inactive rollback authority.
        """
        document = self.selection.bundle_document if self.selection is not None else {}
        return {"authority": MODEL_AUTHORITY, "bundle_id": self.contract.bundle_id,
                "authority_id": self.semantic_authority_id,
                "source_revision": str(document.get("git_revision") or ""),
                "residual": list(self.contract.residual_identities),
                "rollback": "o3",
                "activation_blocked": (True if self.selection is None
                                       else self.selection.activation_blocked)}

    def model_status(self):
        report = super().model_status()
        report["semantic_authority"] = {**self._semantic_authority(),
                                        "provenance": self.contract.provenance()}
        return report

    def _decorate(self, report):
        used = list(self.traversal.aliases_used)
        report = super()._decorate(report)
        if used:
            report["deprecated_aliases"] = [alias_marker(name) for name in used]
        return report

    def semantic_neighbors(self, identifier, *, predicates=None):
        self.traversal.aliases_used = []
        return super().semantic_neighbors(identifier, predicates=predicates)

    def trace(self, source_identifier, target_identifier, *, max_depth=4):
        self.traversal.aliases_used = []
        return super().trace(source_identifier, target_identifier, max_depth=max_depth)

    def impact(self, identifier):
        self.traversal.aliases_used = []
        return super().impact(identifier)

    def verification_coverage(self, requirement_identifier):
        self.traversal.aliases_used = []
        return super().verification_coverage(requirement_identifier)


class ModelAuthorityImpactService(O3ImpactService):
    def impact(self, identifier, *, git_revision):
        report = super().impact(identifier, git_revision=git_revision)
        report["provenance"] = candidate_provenance(
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

    @property
    def is_o3(self) -> bool:
        return False

    def provenance(self) -> dict[str, Any]:
        components = self.bundle_document.get("components") or {}
        return {"kind": MODEL_AUTHORITY, "authority_id": model_authority_id(self.bundle_id),
                "bundle_id": self.bundle_id, "bundle_path": str(self.bundle_path),
                "git_revision": str(self.bundle_document.get("git_revision") or ""),
                "o3_bundle_id": str((components.get("o3") or {}).get("bundle_id") or ""),
                "residual_count": len((components.get("routing") or {}).get("residual") or {}),
                "activation_blocked": self.activation_blocked}


def requested_authority(authority: str | None, environ: Mapping[str, str] | None) -> str:
    env = os.environ if environ is None else environ
    raw = authority if authority is not None else env.get(AUTHORITY_ENV, "")
    return str(raw or "").strip().lower()


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
        raise ModelAuthorityRefused(f"model authority bundle schema mismatch: {path}")
    if document.get("bundle_id") != id_value:
        raise ModelAuthorityRefused("requested model bundle id does not equal the document id")
    return ModelAuthoritySelection(bundle_id=id_value, bundle_path=path, bundle_document=document)


@dataclass(frozen=True)
class ModelAuthority:
    facade: ModelAuthorityFacade
    bundle_id: str
    authority_id: str
    activation_eligible: bool
    o3: Any
    definitions: Any


def load_model_authority(document: Mapping[str, Any], *, root: Path = ROOT, contract: KernelContract,
                         binding: Any, binding_sha256: str, expected_git_revision: str,
                         require_activation_eligible: bool = False,
                         validation_artifacts: Mapping[str, Path] | None = None) -> ModelAuthority:
    from .definition_migration import load_definition_migration_authority
    from .o3_bundle import load_o3_authority

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
    o3 = load_o3_authority(components["o3"]["document"], root=root, contract=contract, binding=binding,
                           binding_sha256=binding_sha256, expected_git_revision=expected_git_revision,
                           require_activation_eligible=require_activation_eligible)
    definitions = load_definition_migration_authority(
        root, contract=contract, binding=binding, require_activation_eligible=True,
        expected_git_revision=expected_git_revision)
    successor = generate_successor_contract(root)
    if _successor_record(successor) != components["successor_contract"]:
        raise ModelAuthorityRefused("successor contract regenerated from the model differs from the bundle")
    _, provisions = load_layers(root)
    routing = compute_routing(legacy=contract, provisions=provisions, successor_contract=successor,
                              register_rows=load_register_rows(root))
    if routing.record() != components["routing"]:
        raise ModelAuthorityRefused("routing recomputed at construction differs from the bundle")
    for name in definitions.identities:
        if routing.providers.get(name) is None or routing.providers[name].layer != "definition":
            raise ModelAuthorityRefused(f"verified definition {name!r} is not routed to the definition layer")
        if routing.providers[name].mapping != definitions.provider.mapping(name):
            raise ModelAuthorityRefused(f"definition layer mapping differs from the verified pair: {name}")
    facade = ModelAuthorityFacade(legacy=contract, o3_facade=o3.facade, routing=routing,
                                  successor_contract=successor, bundle_id=document["bundle_id"],
                                  components=components)
    return ModelAuthority(facade=facade, bundle_id=document["bundle_id"],
                          authority_id=facade.authority_id, activation_eligible=eligible,
                          o3=o3, definitions=definitions)


def build_model_authority_runtime(repo_root: "str | Path" = ROOT,
                                  bundle_path: "str | Path | None" = None,
                                  expected_id: str | None = None, *,
                                  api_url: str, binding_path: Path, expected_git_revision: str,
                                  ontology_path: Path, api_timeout: float = 600.0,
                                  method_conformance: Any = None, method_context_provider: Any = None,
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
    ``require_activation_eligible=False`` (the privileged compare step and
    tests) serves a candidate or ineligible bundle, and ``production=True``
    always requires it. Every failure raises
    :class:`ModelAuthorityRefused`; nothing falls back.
    """
    root = Path(repo_root)
    from de4sdv.sysml_api import client, repository
    from de4sdv.sysml_api.revisions import RevisionBinding

    from .api_binding import OntologyApiBinder
    from .relationship_successor import route_successor_bindings

    selection = resolve_model_selection(bundle_path=bundle_path, bundle_id=expected_id,
                                        environ=environ)
    raw_binding = Path(binding_path).read_bytes()
    binding = RevisionBinding.from_dict(json.loads(raw_binding))
    binding.require_current(expected_git_revision)
    legacy = KernelContract.load(Path(ontology_path))
    binding.require_ontology(legacy.identity)
    authority = load_model_authority(
        selection.bundle_document, root=root, contract=legacy, binding=binding,
        binding_sha256=_sha256_bytes(raw_binding), expected_git_revision=expected_git_revision,
        require_activation_eligible=require_activation_eligible or production,
        validation_artifacts=validation_artifacts)
    facade = authority.facade
    index, routes = route_successor_bindings(facade.profile, binding)
    facade.binding_routes = routes
    model_repository = repository.SysMLRepository(client.ApiClient(api_url, timeout=api_timeout))
    binder = OntologyApiBinder(facade, model_repository, project_id=binding.sysml_project_id,
                               commit_id=binding.sysml_commit_id, kernel_bindings=index)
    traversal = ModelAuthorityTraversal(facade, kernel_bindings=index)
    impact = ModelAuthorityImpactService(repository=model_repository, binding=binding, contract=facade,
                                         binder=binder, traversal=traversal)
    impact.semantic_authority_id = authority.authority_id
    service = ModelAuthorityQueryService(
        repository=model_repository, binding=binding, contract=facade, binder=binder,
        traversal=traversal, impact_service=impact, expected_git_revision=expected_git_revision,
        method_conformance=method_conformance, method_context_provider=method_context_provider,
        semantic_authority_id=authority.authority_id)
    service.selection = replace(selection, activation_blocked=not authority.activation_eligible)
    return service
