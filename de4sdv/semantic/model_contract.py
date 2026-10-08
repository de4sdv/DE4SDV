"""The model-built kernel contract (O4 Wave C2, design E1).

Builds the :class:`~de4sdv.semantic.kernel_contract.KernelContract` the
runtime, ingestion, validators and gates consume from model-generated sources
only:

- the live projection layers (definition batch 1 and batch 2, O2+ native and
  library rows, vocabulary carriers), read and checked by
  :func:`model_authority_runtime.load_layers`;
- the frozen O2-chain layer: the O2 v1-v1.2 Semantic Projection / API
  Representation Profile records (frozen O2 records, owner decision Q7) for
  the 13 identities the O3 cutover migrated. They are read-only data; their
  bytes are pinned by ``docs/method-conformance/frozen-records.json``;
- the relationship-successor contract generated from the model
  (``de4sdv_relationship_carriers.sysml``), with class pins taken from the
  layers above (:func:`model_class_pins`), never from authored YAML;
- the kernel-internal declarations manifest (owner decision D3) for the
  gate's ``exclusions``.

Routing is the model-authority routing (one provider per identity, duplicates
refused). Registered non-retained rows have no provider; they are *refused*
with their register disposition, never served.

No authored ontology file is read here.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from de4sdv.sysml_api.revisions import SEMANTIC_AUTHORITY_SCHEMA, SemanticAuthorityIdentity

from .kernel_contract import (
    KernelContract,
    KernelExternalMapping,
    KernelFileMapping,
    KernelNativeMapping,
    RelationshipMapping,
)

ROOT = Path(__file__).resolve().parents[2]

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


def _mar():
    from . import model_authority_runtime

    return model_authority_runtime


def _refused(message: str) -> Exception:
    return _mar().ModelAuthorityRefused(message)


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


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
            raise _refused(f"frozen O2-chain record unreadable: {relative}: {exc}") from exc
        if not isinstance(document, dict) or document.get("schema") != schema:
            raise _refused(f"frozen O2-chain record schema mismatch: {relative}")
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
    Provision = _mar().Provision
    rows, entries = load_o2_chain_rows(root)
    provisions = []
    for name in O2_CHAIN_RELATIONSHIPS:
        row, entry = rows.get(name), entries.get(name)
        if row is None or entry is None:
            raise _refused(f"frozen O2-chain identity {name!r} lacks a Projection row or Profile entry")
        relation = row.get("relation") or {}
        mechanics = dict(entry.get("serializer_mechanics") or {})
        strategy = str(mechanics.pop("strategy", "") or "")
        mechanics.pop("semantic_strength", None)
        domain = str((relation.get("domain") or {}).get("ontology_class") or "")
        range_ = str((relation.get("range") or {}).get("ontology_class") or "")
        strength = str(relation.get("semantic_strength") or "")
        if not strategy or not domain or not range_ or not strength:
            raise _refused(f"frozen O2-chain identity {name!r} lacks a complete declaration")
        mapping = RelationshipMapping(name=name, strategy=strategy, semantic_strength=strength,
                                      configuration=mechanics, domain=domain, range=range_)
        spec = {"sysml_mapping": {"strategy": strategy, **mechanics}, "domain": domain,
                "range": range_, "semantic_strength": strength}
        provisions.append(Provision(name, "relationship", O2_CHAIN_LAYER, spec=spec,
                                    relationship=mapping))
    for name in O2_CHAIN_CLASSES:
        row = rows.get(name)
        if row is None:
            raise _refused(f"frozen O2-chain class {name!r} lacks a Projection row")
        if name == "VerificationCase":
            construct = row.get("construct") or {}
            native = str((construct.get("native_grounding") or {}).get("identity") or "")
            if str(construct.get("kind") or "") != "native" or not native:
                raise _refused("VerificationCase frozen O2-chain row lacks native grounding")
            mapping: Any = KernelNativeMapping(native)
        else:
            contract = (row.get("grounding") or {}).get("kernel_binding_contract") or {}
            source_file = str(contract.get("source_file") or "")
            declaration = str(contract.get("declaration") or "")
            if not source_file or not declaration:
                raise _refused(f"frozen O2-chain class {name!r} lacks a file/declaration grounding")
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
    records, provisions = _mar().load_layers(root)
    chain = {"layer": O2_CHAIN_LAYER, "frozen": True, "chain": o2_chain_records(root),
             "identities": sorted(O2_CHAIN_IDENTITIES)}
    return [chain] + records, o2_chain_provisions(root) + list(provisions)


def load_kernel_exclusions(root: Path = ROOT) -> tuple[str, dict[str, dict[str, str]]]:
    """Governed directory and kernel-internal declarations (D3 manifest)."""
    import yaml

    document = yaml.safe_load((Path(root) / KERNEL_INTERNAL_PATH).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise _refused(f"{KERNEL_INTERNAL_PATH} must be a mapping")
    directory = document.get("governed_directory")
    declarations = document.get("declarations")
    if not isinstance(directory, str) or not directory or not isinstance(declarations, dict):
        raise _refused(f"{KERNEL_INTERNAL_PATH} lacks governed_directory/declarations")
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
    raise _refused(f"unsupported class mapping {mapping!r}")


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


def build_model_contract(root: Path = ROOT) -> KernelContract:
    """Build the kernel contract from the model-generated layers (fail closed)."""
    root = Path(root)
    mar = _mar()
    records, provisions = load_model_layers(root)
    chain = [p for p in provisions if p.layer == O2_CHAIN_LAYER]
    layered = [p for p in provisions if p.layer != O2_CHAIN_LAYER]
    successor = generate_model_successor_contract(root, records=records, provisions=provisions)
    register = mar.load_register_rows(root)
    routing = mar.compute_routing(legacy=None, provisions=layered, successor_contract=successor,
                                  register_rows=register, seed=chain)
    if routing.duplicates:
        raise _refused("duplicate providers: " + "; ".join(routing.duplicates))
    refused = register_refusals(register)
    for name, reason in (successor.get("retired") or {}).items():
        refused.setdefault(name, f"retired by the model successor contract: {reason}")
    class_mappings: dict[str, Any] = {}
    relationship_mappings: dict[str, Any] = {}
    relationships: dict[str, Any] = {}
    retired = set(mar.DEPRECATED_ALIASES) | set(successor.get("retired") or ())
    for name, provision in sorted(routing.providers.items()):
        if name in refused:
            raise _refused(f"{name}: refused identity is also provided by {provision.layer}")
        if provision.kind == "class":
            class_mappings[name] = provision.mapping
        elif provision.kind == "relationship":
            if name in retired:
                continue
            relationships[name] = json.loads(json.dumps(provision.spec or {}))
            relationship_mappings[name] = provision.relationship
    classes = {name: {"kernel": _mapping_record(mapping)} for name, mapping in class_mappings.items()}
    directory, exclusions = load_kernel_exclusions(root)
    content = contract_content(class_mappings, relationship_mappings, relationships, refused)
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
    )


__all__ = ["build_model_contract", "contract_content", "generate_model_successor_contract",
           "load_kernel_exclusions", "load_model_layers", "model_class_pins", "o2_chain_provisions",
           "o2_chain_records", "register_refusals", "O2_CHAIN_IDENTITIES", "O2_CHAIN_LAYER"]
