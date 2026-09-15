"""O3 readiness — semantic-authority bundle extraction and same-revision
equivalence comparison (read-only planning evidence).

This module is the planning/evidence machinery for the O3 authority-
transition readiness package. It NEVER switches, routes, or activates
runtime authority:

- it is not imported by the runtime/query path (locked by tests);
- it performs no writes except the committed O3 scope document through its
  companion CLI (``scripts/generate_o3_equivalence_scope.py``);
- every comparison fails closed on any unresolved mismatch.

The readiness question answered mechanically:

- which authority bundle currently governs each of the 13 reviewed O2
  identities — the old bundle (authored ontology YAML + kernel contract +
  ingestion-validated kernel bindings + runtime strategy implementations)
  or the proposed new bundle (authoritative model revision + the DE4SDV
  Semantic Projection chain through v1.2 + the SysML API Representation
  Profile chain through v1.2);
- whether the two bundles DECLARE the same semantics for every identity
  across SEPARATE comparison dimensions — declared semantic core (domain,
  range, canonical direction, semantic strength), representation contract
  (old mapping mechanics vs new profile serializer mechanics), grounding
  identity (kernel declaration / library grounding), claim boundary, and
  scope/exclusions — with support-state preservation recorded separately and
  runtime behavior honestly NOT_YET_COMPARABLE until the same-revision
  comparison harness runs at cutover;
- what exact same-revision comparison the future cutover must execute
  before any activation claim (the comparison manifest and result
  comparator below).

Nothing in this module is a conformance verdict about the O3 transition:
it is the evidence/design package that must be independently reviewed
before an O3 implementation may begin.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .kernel_contract import (
    KernelContract,
    KernelExternalMapping,
    KernelFileMapping,
    KernelNativeMapping,
)

ROOT = Path(__file__).resolve().parents[2]

ONTOLOGY_PATH = "approach/framework/ontology/de4sdv-basic-ontology.yaml"
KERNEL_CONTRACT_PATH = "de4sdv/semantic/kernel_contract.py"
O1_INVENTORY_PATH = "docs/method-conformance/o1/semantic-authority-inventory.json"
O3_SCOPE_PATH = "docs/method-conformance/o3/o3-equivalence-scope.json"
O3_SCOPE_SCHEMA = "de4sdv.o3-equivalence-scope/v1"

#: Reviewed O2 migration surface — exactly these identities, no fourteenth.
O2_SURFACE_O21 = (
    "MethodPhase",
    "MethodContractObligation",
    "EvaluationScopeMembership",
    "EvaluationSourceKind",
    "TestedScopeDeclaration",
    "RetainedExecutionRecordReference",
    "AcceptanceAttestationReference",
)
O2_SURFACE_O22 = ("VerificationCase", "hasSubject", "verifiedBy")
O2_SURFACE_O23 = (
    "derivesRequirementFromNeed",
    "derivedRequirementsOfNeed",
    "hasRelevantArchitecture",
)
O3_SCOPE_IDENTITIES = O2_SURFACE_O21 + O2_SURFACE_O22 + O2_SURFACE_O23

O3_SCOPE_CLASSES = (
    "MethodPhase",
    "MethodContractObligation",
    "EvaluationScopeMembership",
    "EvaluationSourceKind",
    "TestedScopeDeclaration",
    "RetainedExecutionRecordReference",
    "AcceptanceAttestationReference",
    "VerificationCase",
)
O3_SCOPE_RELATIONSHIPS = (
    "hasSubject",
    "verifiedBy",
    "derivesRequirementFromNeed",
    "derivedRequirementsOfNeed",
    "hasRelevantArchitecture",
)

#: Identities that must NOT be migrated by this scope (reviewed exclusions).
EXCLUDED_IDENTITIES = (
    "MethodEvaluationScope",
    "DerivesFromNeed",
    "derivesNeedFromConcern",
    "realizedBy",
    "specifiesFunction",
    "hasRelevantEvidenceContract",
    "EvidenceContract",
    "allocatedTo",
    "deployedTo",
)

#: The generated O2 artifact chain, in dependency order.
O2_CHAIN = (
    ("docs/method-conformance/o2/semantic-projection-v1.json", "de4sdv.semantic-projection.v1"),
    ("docs/method-conformance/o2/api-representation-profile-v1.json", "de4sdv.api-representation-profile.v1"),
    ("docs/method-conformance/o2/semantic-projection-v1.1.json", "de4sdv.semantic-projection.v1.1"),
    ("docs/method-conformance/o2/api-representation-profile-v1.1.json", "de4sdv.api-representation-profile.v1.1"),
    ("docs/method-conformance/o2/semantic-projection-v1.2.json", "de4sdv.semantic-projection.v1.2"),
    ("docs/method-conformance/o2/api-representation-profile-v1.2.json", "de4sdv.api-representation-profile.v1.2"),
)

#: Runtime/query implementation files of the old authority path (the O3
#: routing seam touches exactly these; recorded here for the bundle record).
OLD_BUNDLE_RUNTIME_FILES = (
    "de4sdv/semantic/runtime.py",
    "de4sdv/semantic/query.py",
    "de4sdv/semantic/traversal.py",
    "de4sdv/semantic/impact.py",
    "de4sdv/semantic/api_binding.py",
    "de4sdv/semantic/kernel_binding_index.py",
    "de4sdv/semantic/kernel_contract.py",
    "de4sdv/sysml_api/revisions.py",
)

#: Mechanics fields that must remain in the profile, never in projection rows.
PROFILE_ONLY_MECHANICS = (
    "strategy",
    "query_direction",
    "need_role",
    "requirement_role",
    "relationship_types",
    "source_property",
    "target_property",
    "source_types",
    "membership_types",
    "reference_property",
    "member_property",
    "owner_types",
    "owner_membership_types",
    "element_types",
    "exclude_source_specializations_of",
    "connection_definition",
    "source_lineage_of",
    "target_lineage_of",
    "ReferenceSubsetting",
    "metaclass",
)

#: Classification vocabulary (exactly one per comparison dimension).
CLASSIFICATIONS = (
    "EQUIVALENT",
    "INTENTIONAL_MIGRATION_REVIEW_REQUIRED",
    "BLOCKING_MISMATCH",
    "UNSUPPORTED_BOTH",
    "NOT_YET_COMPARABLE",
)

K_PAIR = ("derivesRequirementFromNeed", "derivedRequirementsOfNeed")

K_NATIVE_DIRECTION = "Need -> Requirement"
K_CLAIM_REQUIRED = ("provenance only", "neither satisfaction nor logical implication")


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


BASE_REVISION_POLICY = (
    "the permanent main revision this readiness package was prepared "
    "against; it identifies the Git revision for the old-bundle record and "
    "is validated to exist and to remain an ancestor of the checked-out "
    "revision. Byte identity of the old bundle is carried by the ontology, "
    "kernel-contract, and runtime-file digests below (squash-safe: no "
    "feature-branch commit is ever recorded)."
)


def _git(root: Path, *args: str) -> str:
    import subprocess

    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(
            f"git {' '.join(args)} failed in {root}: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def resolve_comparison_base_revision(root: Path) -> str:
    """Resolve the permanent comparison-base revision (origin/main if known)."""
    try:
        revision = _git(root, "rev-parse", "origin/main")
    except ValueError:
        revision = _git(root, "rev-parse", "HEAD")
    if len(revision) != 40 or any(
        character not in "0123456789abcdef" for character in revision
    ):
        raise ValueError(f"unresolved comparison base revision: {revision!r}")
    return revision


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be a JSON object")
    return value


# ---------------------------------------------------------------------------
# O2 chain loading
# ---------------------------------------------------------------------------


def load_o2_chain(root: Path) -> dict[str, dict[str, Any]]:
    """Load the six committed O2 artifacts with schema/digest verification."""
    chain: dict[str, dict[str, Any]] = {}
    for rel, schema in O2_CHAIN:
        path = root / rel
        if not path.exists():
            raise ValueError(f"O2 chain artifact missing: {rel}")
        document = _json(path)
        if document.get("schema") != schema:
            raise ValueError(
                f"O2 chain schema mismatch for {rel}: "
                f"{document.get('schema')!r} != {schema!r}"
            )
        chain[rel] = {
            "schema": schema,
            "sha256": sha256_file(path),
            "source_revision": str(
                (document.get("binding") or {}).get("source_revision") or ""
            ),
            "api_binding": str(
                ((document.get("binding") or {}).get("api_binding") or {}).get(
                    "status"
                )
                or ""
            ),
            "document": document,
        }
    return chain


def chain_rows(chain: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index every identity row across the chain by identity name."""
    rows: dict[str, dict[str, Any]] = {}
    for rel, _schema in O2_CHAIN:
        document = chain[rel]["document"]
        for section in ("concepts", "predicates"):
            for row in document.get(section, []):
                identity = row.get("identity") or row.get("for_concept")
                if not identity:
                    continue
                rows[identity] = {"artifact": rel, "section": section, "row": row}
    return rows


def chain_profile_entries(chain: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index every profile entry across the chain by identity/concept name."""
    entries: dict[str, dict[str, Any]] = {}
    for rel, _schema in O2_CHAIN:
        if "profile" not in rel:
            continue
        document = chain[rel]["document"]
        for entry in document.get("profiles", []):
            identity = entry.get("for_identity") or entry.get("for_concept")
            if not identity:
                continue
            entries[identity] = {"artifact": rel, "entry": entry}
    return entries


# ---------------------------------------------------------------------------
# Old authority bundle extraction (ontology YAML + kernel contract)
# ---------------------------------------------------------------------------


def _class_old_record(contract: KernelContract, name: str) -> dict[str, Any]:
    spec = contract.classes.get(name)
    if not isinstance(spec, dict):
        raise ValueError(f"old bundle: ontology class missing: {name}")
    mapping = contract.mapping(name)
    if isinstance(mapping, KernelFileMapping):
        declared: dict[str, str] = {
            "kernel_mapping_kind": "file",
            "source_file": mapping.file,
            "declaration": mapping.declaration,
        }
        consumption = "kernel-binding identity resolution"
    elif isinstance(mapping, KernelNativeMapping):
        declared = {"kernel_mapping_kind": "native", "native": mapping.native}
        consumption = "native-construct vocabulary"
    elif isinstance(mapping, KernelExternalMapping):
        declared = {"kernel_mapping_kind": "external", "external": mapping.external}
        consumption = "external reference"
    else:
        raise ValueError(f"old bundle: unsupported kernel mapping for {name}")
    return {
        "kind": "class",
        "declared": declared,
        "runtime_status": {
            "consumption": consumption,
            "queryable_as_predicate": False,
        },
    }


def _relationship_old_record(contract: KernelContract, name: str) -> dict[str, Any]:
    spec = contract.relationships.get(name)
    if not isinstance(spec, dict):
        raise ValueError(f"old bundle: ontology relationship missing: {name}")
    mapping = contract.relationship_mapping(name)
    config = dict(mapping.configuration)
    strategy = mapping.strategy
    blocked = str(mapping.range or "") == "EvidenceContract"
    # Old canonical query direction: the derivation-connection mapping
    # declares its query side through source/target lineage; every other
    # strategy queries the declared domain->range claim.
    if strategy == "derivation-connection":
        old_canonical = (
            f"{config.get('source_lineage_of')} -> {config.get('target_lineage_of')}"
        )
        native_direction = "Need -> Requirement"
    else:
        old_canonical = f"{mapping.domain} -> {mapping.range}"
        native_direction = old_canonical
    return {
        "kind": "relationship",
        "declared": {
            "domain": mapping.domain,
            "range": mapping.range,
            "strategy": strategy,
            "semantic_strength": mapping.semantic_strength,
            "configuration": config,
        },
        "runtime_status": {
            "strategy_executed": strategy not in {"external"},
            "blocked": blocked,
            "queryable_as_predicate": strategy not in {"external"} and not blocked,
            "old_canonical_direction": old_canonical,
            "old_native_direction": native_direction,
        },
    }


def extract_old_bundle(root: Path, contract: KernelContract) -> dict[str, Any]:
    """Machine-readable description of the current OLD authority bundle."""
    runtime_files = {}
    for rel in OLD_BUNDLE_RUNTIME_FILES:
        path = root / rel
        if not path.exists():
            raise ValueError(f"old bundle runtime file missing: {rel}")
        runtime_files[rel] = sha256_file(path)
    identities: dict[str, Any] = {
        name: _class_old_record(contract, name) for name in O3_SCOPE_CLASSES
    }
    identities.update(
        {
            name: _relationship_old_record(contract, name)
            for name in O3_SCOPE_RELATIONSHIPS
        }
    )
    # Cross-reference: the old path's machine-readable case-type population
    # (the API types through which the verifiedBy strategy resolves cases)
    # feeds the VerificationCase grounding comparison — the standard-library
    # roles must cover exactly the same type population on the new side.
    verified_by = identities.get("verifiedBy")
    verification_case = identities.get("VerificationCase")
    if isinstance(verified_by, dict) and isinstance(verification_case, dict):
        verification_case["related_case_element_types"] = sorted(
            str(item)
            for item in (
                (verified_by["declared"].get("configuration") or {}).get(
                    "element_types", []
                )
            )
        )
    return {
        "ontology": {
            "path": ONTOLOGY_PATH,
            "sha256": sha256_file(root / ONTOLOGY_PATH),
        },
        "kernel_contract_module": {
            "path": KERNEL_CONTRACT_PATH,
            "sha256": sha256_file(root / KERNEL_CONTRACT_PATH),
        },
        "kernel_contract_identity": contract.identity.to_dict(),
        "runtime_files": runtime_files,
        "identities": identities,
    }


# ---------------------------------------------------------------------------
# New (proposed O3) bundle extraction from the committed O2 chain
# ---------------------------------------------------------------------------


def _relationship_new_record(
    chain: dict[str, dict[str, Any]], identity: str
) -> dict[str, Any]:
    rows = chain_rows(chain)
    entry = rows.get(identity)
    if entry is None:
        raise ValueError(f"new bundle: identity missing from O2 chain: {identity}")
    relation = entry["row"].get("relation")
    if not isinstance(relation, dict):
        raise ValueError(f"new bundle: relationship row has no relation: {identity}")
    profiles = chain_profile_entries(chain)
    profile_entry = profiles.get(identity)
    mechanics: dict[str, Any] = {}
    if profile_entry is not None:
        mechanics = dict(profile_entry["entry"].get("serializer_mechanics") or {})
    return {
        "kind": "relationship",
        "o2_artifact": entry["artifact"],
        "declared": {
            "domain": str((relation.get("domain") or {}).get("ontology_class") or ""),
            "range": str((relation.get("range") or {}).get("ontology_class") or ""),
            "canonical_direction": str(relation.get("canonical_direction") or ""),
            "semantic_strength": str(relation.get("semantic_strength") or ""),
            "claim_boundary": str(relation.get("claim_boundary") or ""),
            "native_grounding_note": str(
                (relation.get("native_grounding") or {}).get("note") or ""
            ),
            "native_construct": str(
                (relation.get("native_grounding") or {}).get("native_construct") or ""
            ),
            "native_modeled_direction": str(
                relation.get("native_modeled_direction") or ""
            ),
            "scope_restriction_axes": [
                str(item.get("axis") or "")
                for item in relation.get("scope_restrictions", [])
                if isinstance(item, dict)
            ],
        },
        "representation_mechanics": mechanics,
        "profile_entry_present": profile_entry is not None,
        "exclusion_lineage_class": str(
            (relation.get("exclusion_lineage") or {}).get("ontology_class") or ""
        ),
        "support_state": str(entry["row"].get("support_state") or ""),
    }


def _class_new_record(
    chain: dict[str, dict[str, Any]], identity: str
) -> dict[str, Any]:
    rows = chain_rows(chain)
    entry = rows.get(identity)
    if entry is None:
        raise ValueError(f"new bundle: identity missing from O2 chain: {identity}")
    row = entry["row"]
    profiles = chain_profile_entries(chain)
    profile_entry = profiles.get(identity)
    grounding_mechanics: dict[str, Any] = {}
    if profile_entry is not None:
        grounding_mechanics = dict(
            profile_entry["entry"].get("library_grounding_mechanics") or {}
        )
    if identity == "VerificationCase":
        construct = row.get("construct") or {}
        declared: dict[str, Any] = {
            "kernel_mapping_kind": str(construct.get("kind") or ""),
            "native_grounding": str(
                (construct.get("native_grounding") or {}).get("identity") or ""
            ),
        }
    else:
        grounding = (row.get("grounding") or {}).get("kernel_binding_contract") or {}
        declared = {
            "kernel_mapping_kind": "file",
            "source_file": str(grounding.get("source_file") or ""),
            "declaration": str(grounding.get("declaration") or ""),
            "api_metaclass": str(grounding.get("api_metaclass") or ""),
        }
    return {
        "kind": "class",
        "o2_artifact": entry["artifact"],
        "declared": declared,
        "library_grounding_mechanics": grounding_mechanics,
        "profile_entry_present": profile_entry is not None,
        "support_state": str(row.get("support_state") or ""),
    }


def extract_new_bundle(chain: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Machine-readable description of the proposed NEW O3 bundle."""
    return {
        "chain": [
            {
                "path": rel,
                "schema": chain[rel]["schema"],
                "sha256": chain[rel]["sha256"],
                "source_revision": chain[rel]["source_revision"],
                "api_binding": chain[rel]["api_binding"],
            }
            for rel, _schema in O2_CHAIN
        ],
        "identities": {
            **{
                name: _class_new_record(chain, name)
                for name in O3_SCOPE_CLASSES
            },
            **{
                name: _relationship_new_record(chain, name)
                for name in O3_SCOPE_RELATIONSHIPS
            },
        },
    }


# ---------------------------------------------------------------------------
# Declared-semantics comparison (old vs new authority bundles)
# ---------------------------------------------------------------------------


def compare_declared(
    identity: str,
    old_identity: dict[str, Any] | None,
    new_identity: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compare the declared semantics of one identity across the two bundles.

    Exact-field comparison; any mismatch is a BLOCKING_MISMATCH (or a
    reviewed intentional migration when listed in INTENTIONAL_MIGRATIONS,
    which is empty until a migration is independently reviewed).
    """
    if old_identity is None or new_identity is None:
        return {
            "classification": "BLOCKING_MISMATCH",
            "reasons": ["missing-identity"],
            "fields": {},
        }
    fields: dict[str, dict[str, Any]] = {}
    mismatches: list[str] = []

    def compare(field_name: str, old_value: Any, new_value: Any) -> None:
        ok = old_value == new_value
        fields[field_name] = {"old": old_value, "new": new_value, "ok": ok}
        if not ok:
            mismatches.append(field_name)

    if old_identity["kind"] != new_identity["kind"]:
        mismatches.append("identity-kind")
        fields["kind"] = {
            "old": old_identity["kind"],
            "new": new_identity["kind"],
            "ok": False,
        }
        return {
            "classification": "BLOCKING_MISMATCH",
            "reasons": mismatches,
            "fields": fields,
        }

    old_declared = old_identity["declared"]
    new_declared = new_identity["declared"]
    if old_identity["kind"] == "relationship":
        compare("domain", old_declared.get("domain"), new_declared.get("domain"))
        compare("range", old_declared.get("range"), new_declared.get("range"))
        compare(
            "canonical_direction",
            old_identity["runtime_status"].get("old_canonical_direction"),
            new_declared.get("canonical_direction"),
        )
        compare(
            "semantic_strength",
            old_declared.get("semantic_strength"),
            new_declared.get("semantic_strength"),
        )
    else:
        compare(
            "kernel_mapping_kind",
            old_declared.get("kernel_mapping_kind"),
            new_declared.get("kernel_mapping_kind"),
        )

    classification = "EQUIVALENT" if not mismatches else "BLOCKING_MISMATCH"
    return {"classification": classification, "reasons": mismatches, "fields": fields}


# ---------------------------------------------------------------------------
# Representation contract, grounding identity, claim boundary, scope
# ---------------------------------------------------------------------------


#: Reviewed representation-contract field sets: the old mapping mechanics
#: (ontology sysml_mapping configuration + strategy) and the new profile
#: serializer mechanics must carry EXACTLY these fields with equal values.
#: Any missing, extra, or differing field is load-bearing drift.
EXPECTED_REPRESENTATION_FIELDS: dict[str, tuple[str, ...]] = {
    "hasSubject": (
        "strategy",
        "membership_types",
        "member_property",
        "owner_types",
    ),
    "verifiedBy": (
        "strategy",
        "membership_types",
        "element_types",
        "owner_membership_types",
        "reference_property",
        "direction",
    ),
    "derivesRequirementFromNeed": (
        "strategy",
        "connection_definition",
        "need_role",
        "requirement_role",
        "query_direction",
        "source_lineage_of",
        "target_lineage_of",
    ),
    "derivedRequirementsOfNeed": (
        "strategy",
        "connection_definition",
        "need_role",
        "requirement_role",
        "query_direction",
        "source_lineage_of",
        "target_lineage_of",
    ),
    "hasRelevantArchitecture": (
        "strategy",
        "relationship_types",
        "direction",
        "source_property",
        "target_property",
        "source_types",
        "exclude_source_specializations_of",
    ),
}

#: Reviewed scope/exclusion axes each new-side relationship must declare
#: (they encode the old path's enforcement points; hasRelevantArchitecture
#: additionally compares the exclusion lineage class against the old mapping).
EXPECTED_SCOPE_AXES: dict[str, frozenset[str]] = {
    "hasSubject": frozenset({"source", "target"}),
    "verifiedBy": frozenset({"source"}),
    "derivesRequirementFromNeed": frozenset({"role-identity", "witness", "claim"}),
    "derivedRequirementsOfNeed": frozenset({"role-identity", "witness", "claim"}),
    "hasRelevantArchitecture": frozenset(
        {"source-domain", "source-types", "exclusion", "witness"}
    ),
}

#: Reviewed claim-boundary contract: the new-side claim text must satisfy the
#: old strength class's boundary (the field carrying the claim text and the
#: required fragments).
CLAIM_CONTRACT: dict[str, tuple[str, tuple[str, ...]]] = {
    "derivesRequirementFromNeed": (
        "claim_boundary",
        ("provenance only", "neither satisfaction nor logical implication"),
    ),
    "derivedRequirementsOfNeed": (
        "claim_boundary",
        ("provenance only", "neither satisfaction nor logical implication"),
    ),
    "hasSubject": (
        "native_grounding_note",
        ("narrowed by the declared scope restrictions",),
    ),
    "verifiedBy": (
        "native_grounding_note",
        ("coverage relation only",),
    ),
    "hasRelevantArchitecture": (
        "native_grounding_note",
        ("by itself is NOT hasRelevantArchitecture",),
    ),
}

#: Reviewed VerificationCase standard-library anchors (the profile's
#: library_grounding_mechanics must name exactly these roles).
VERIFICATIONCASE_LIBRARY_ANCHORS = {
    "definition_role": "VerificationCases::VerificationCase",
    "usage_role": "VerificationCases::verificationCases",
}

#: The VerificationCase standard-library grounding proof is not bound to the
#: cutover revision on EITHER authority path: the old side's parity evidence
#: and the retained privileged run are historical, and the new side's proof
#: step has not been executed at the cutover revision yet.
VERIFICATIONCASE_PROOF_MISSING = (
    "standard-library grounding proof is not bound to the cutover revision on "
    "either authority path: the reviewed parity evidence and the retained "
    "privileged run (34576049742 at candidate 0a23902370) are historical; the "
    "O3 cutover must execute the profile's controlled standard-library proof "
    "(licensed exporter anchor resolution + read-back) at the exact cutover "
    "revision before this dimension can classify beyond NOT_YET_COMPARABLE"
)


def _canonical_value(value: Any) -> Any:
    if isinstance(value, list):
        try:
            return sorted(value, key=lambda item: json.dumps(item, sort_keys=True))
        except TypeError:
            return sorted(str(item) for item in value)
    return value


def compare_representation_contract(
    identity: str,
    old_identity: dict[str, Any] | None,
    new_identity: dict[str, Any] | None,
) -> dict[str, Any]:
    """Old mapping mechanics vs the new profile serializer mechanics.

    Serializer mechanics are representation, not Projection semantics: this
    is an O3 authority-path parity check, never a change to the
    Projection/Profile separation. Every reviewed mechanics field must be
    present on BOTH sides with an equal value; missing, extra, or differing
    fields are load-bearing drift (BLOCKING_MISMATCH).
    """
    if identity not in EXPECTED_REPRESENTATION_FIELDS:
        return {
            "classification": "EQUIVALENT",
            "reasons": [],
            "fields": {},
            "detail": "no representation mechanics on either authority path",
        }
    if old_identity is None or new_identity is None:
        return {
            "classification": "BLOCKING_MISMATCH",
            "reasons": ["missing-identity"],
            "fields": {},
        }
    old_declared = old_identity["declared"]
    old_mechanics: dict[str, Any] = {"strategy": old_declared.get("strategy")}
    old_mechanics.update(old_declared.get("configuration") or {})
    new_mechanics = dict(new_identity.get("representation_mechanics") or {})
    # semantic_strength is a declared semantic-core field, echoed in the new
    # mechanics for the profile's own consistency checks; exclude it here.
    new_mechanics.pop("semantic_strength", None)

    expected = set(EXPECTED_REPRESENTATION_FIELDS[identity])
    old_keys, new_keys = set(old_mechanics), set(new_mechanics)
    fields: dict[str, dict[str, Any]] = {}
    reasons: list[str] = []
    for key in sorted(expected - old_keys):
        reasons.append(f"missing-old-mechanics:{key}")
    for key in sorted(expected - new_keys):
        reasons.append(f"missing-new-mechanics:{key}")
    for key in sorted((old_keys | new_keys) - expected):
        reasons.append(f"unreviewed-mechanics-field:{key}")
    for key in sorted(expected & old_keys & new_keys):
        old_value = _canonical_value(old_mechanics[key])
        new_value = _canonical_value(new_mechanics[key])
        ok = old_value == new_value
        fields[key] = {"old": old_value, "new": new_value, "ok": ok}
        if not ok:
            reasons.append(key)
    if identity in K_PAIR:
        # The K pair's modeled native direction is part of the compared
        # contract (reviewed constant on the old side; declared on the new).
        old_native = old_identity["runtime_status"].get("old_native_direction")
        new_native = new_identity["declared"].get("native_modeled_direction")
        ok = old_native == new_native
        fields["native_modeled_direction"] = {
            "old": old_native,
            "new": new_native,
            "ok": ok,
        }
        if not ok:
            reasons.append("native_modeled_direction")
    classification = "EQUIVALENT" if not reasons else "BLOCKING_MISMATCH"
    return {"classification": classification, "reasons": reasons, "fields": fields}


def compare_grounding_identity(
    identity: str,
    old_identity: dict[str, Any] | None,
    new_identity: dict[str, Any] | None,
) -> dict[str, Any]:
    """Grounding-identity comparison (kernel declaration / library grounding).

    File-mapped classes compare declaration grounding exactly (source file,
    declaration, and the API metaclass derived from the declaration).
    ``VerificationCase`` compares the construct identity, the covered type
    population, and the reviewed library anchors — never ``native == native``
    and never API metaclass equality alone; the standard-library grounding
    PROOF remains pending until it is executed at the cutover revision
    (UG-28), so a clean construct comparison still classifies
    NOT_YET_COMPARABLE, and any construct/anchor/type-population drift is a
    BLOCKING_MISMATCH.
    """
    from .kernel_contract import declaration_identity

    if old_identity is None or new_identity is None:
        return {
            "classification": "BLOCKING_MISMATCH",
            "reasons": ["missing-identity"],
            "fields": {},
        }
    old_declared = old_identity["declared"]
    new_declared = new_identity["declared"]
    fields: dict[str, dict[str, Any]] = {}
    reasons: list[str] = []

    if identity == "VerificationCase":
        kind_ok = (
            old_declared.get("kernel_mapping_kind")
            == new_declared.get("kernel_mapping_kind")
            == "native"
        )
        fields["construct_kind"] = {
            "old": old_declared.get("kernel_mapping_kind"),
            "new": new_declared.get("kernel_mapping_kind"),
            "ok": kind_ok,
        }
        if not kind_ok:
            reasons.append("construct-kind")
        new_grounding = str(new_declared.get("native_grounding") or "")
        construct_identity_ok = "VerificationCase" in new_grounding
        fields["construct_identity"] = {
            "old": "native verification-case construct (authored ontology)",
            "new": new_grounding,
            "ok": construct_identity_ok,
        }
        if not construct_identity_ok:
            reasons.append("construct-identity")
        mechanics = new_identity.get("library_grounding_mechanics") or {}
        anchors = {
            role: str((mechanics.get(role) or {}).get("library_identity") or "")
            for role in ("definition_role", "usage_role")
        }
        anchors_ok = anchors == VERIFICATIONCASE_LIBRARY_ANCHORS
        fields["library_anchors"] = {
            "old": "reviewed parity evidence (authored ontology carries no structured anchors)",
            "new": anchors,
            "ok": anchors_ok,
        }
        if not anchors_ok:
            reasons.append("library-anchors")
        old_types = set(old_identity.get("related_case_element_types") or [])
        new_types = {
            role: str((mechanics.get(role) or {}).get("applies_to") or "")
            for role in ("definition_role", "usage_role")
        }
        type_population_ok = bool(old_types) and set(new_types.values()) == old_types
        fields["grounded_type_population"] = {
            "old": sorted(old_types),
            "new": sorted(set(new_types.values())),
            "ok": type_population_ok,
        }
        if not type_population_ok:
            reasons.append("grounded-type-population")
        if reasons:
            return {
                "classification": "BLOCKING_MISMATCH",
                "reasons": reasons,
                "fields": fields,
            }
        return {
            "classification": "NOT_YET_COMPARABLE",
            "reasons": [],
            "fields": fields,
            "missing_evidence": VERIFICATIONCASE_PROOF_MISSING,
        }

    if old_declared.get("kernel_mapping_kind") == "file":
        for key in ("source_file", "declaration"):
            old_value = old_declared.get(key)
            new_value = new_declared.get(key)
            ok = old_value == new_value
            fields[key] = {"old": old_value, "new": new_value, "ok": ok}
            if not ok:
                reasons.append(key)
        expected_type = declaration_identity(str(old_declared.get("declaration")))[1]
        new_type = new_declared.get("api_metaclass")
        ok = expected_type == new_type
        fields["api_metaclass"] = {"old": expected_type, "new": new_type, "ok": ok}
        if not ok:
            reasons.append("api_metaclass")
        return {
            "classification": "EQUIVALENT" if not reasons else "BLOCKING_MISMATCH",
            "reasons": reasons,
            "fields": fields,
        }

    # Relationships: the new native construct must name the same witness
    # kind the old strategy executes (structural, mechanics-derived token).
    mechanics = new_identity.get("representation_mechanics") or {}
    if identity in K_PAIR:
        token = str(mechanics.get("connection_definition") or "")
    elif identity == "hasSubject":
        token = str((mechanics.get("membership_types") or [""])[0] or "")
    elif identity == "verifiedBy":
        token = str((mechanics.get("membership_types") or [""])[0] or "")
    elif identity == "hasRelevantArchitecture":
        token = str((mechanics.get("relationship_types") or [""])[0] or "")
    else:
        raise ValueError(f"grounding comparison: unexpected identity {identity!r}")
    construct = str(new_declared.get("native_construct") or "")
    ok = bool(token) and token in construct
    fields["witness_construct"] = {"old": token, "new": construct, "ok": ok}
    if not ok:
        reasons.append("witness-construct")
    return {
        "classification": "EQUIVALENT" if not reasons else "BLOCKING_MISMATCH",
        "reasons": reasons,
        "fields": fields,
    }


def compare_claim_boundary(
    identity: str,
    old_identity: dict[str, Any] | None,
    new_identity: dict[str, Any] | None,
) -> dict[str, Any]:
    """Claim-boundary comparison: the new-side claim text must satisfy the
    old strength class's reviewed boundary contract."""
    if identity not in CLAIM_CONTRACT:
        return {
            "classification": "EQUIVALENT",
            "reasons": [],
            "fields": {},
            "detail": "no predicate claim on either authority path",
        }
    if old_identity is None or new_identity is None:
        return {
            "classification": "BLOCKING_MISMATCH",
            "reasons": ["missing-identity"],
            "fields": {},
        }
    text_field, fragments = CLAIM_CONTRACT[identity]
    text = str(new_identity["declared"].get(text_field) or "")
    missing = [fragment for fragment in fragments if fragment not in text]
    ok = not missing
    fields = {
        "claim_text_source": text_field,
        "claim_text": text[:220],
        "required_fragments": list(fragments),
        "missing_fragments": missing,
        "ok": ok,
    }
    return {
        "classification": "EQUIVALENT" if ok else "BLOCKING_MISMATCH",
        "reasons": [] if ok else ["claim-boundary-contract"],
        "fields": fields,
    }


def compare_scope_exclusions(
    identity: str,
    old_identity: dict[str, Any] | None,
    new_identity: dict[str, Any] | None,
) -> dict[str, Any]:
    """Scope/exclusion comparison: the new-side restriction axes must match
    the reviewed enforcement set; hasRelevantArchitecture additionally
    compares the exclusion lineage class against the old mapping value."""
    if identity not in EXPECTED_SCOPE_AXES:
        return {
            "classification": "EQUIVALENT",
            "reasons": [],
            "fields": {},
            "detail": "no scope/exclusion restrictions on either authority path",
        }
    if old_identity is None or new_identity is None:
        return {
            "classification": "BLOCKING_MISMATCH",
            "reasons": ["missing-identity"],
            "fields": {},
        }
    expected_axes = set(EXPECTED_SCOPE_AXES[identity])
    new_axes = set(new_identity["declared"].get("scope_restriction_axes") or [])
    fields: dict[str, dict[str, Any]] = {}
    reasons: list[str] = []
    axes_ok = new_axes == expected_axes
    fields["scope_axes"] = {
        "old": sorted(expected_axes),
        "new": sorted(new_axes),
        "ok": axes_ok,
    }
    if not axes_ok:
        reasons.append("scope-axes")
    if identity == "hasRelevantArchitecture":
        old_exclusion = (
            old_identity["declared"].get("configuration") or {}
        ).get("exclude_source_specializations_of")
        new_exclusion = new_identity.get("exclusion_lineage_class") or ""
        exclusion_ok = bool(old_exclusion) and old_exclusion == new_exclusion
        fields["exclusion_lineage"] = {
            "old": old_exclusion,
            "new": new_exclusion,
            "ok": exclusion_ok,
        }
        if not exclusion_ok:
            reasons.append("exclusion-lineage")
    classification = "EQUIVALENT" if not reasons else "BLOCKING_MISMATCH"
    return {"classification": classification, "reasons": reasons, "fields": fields}


#: The comparison dimensions exposed per identity (the overall static result
#: must never be EQUIVALENT merely because the semantic core matches).
COMPARISON_DIMENSIONS = (
    "declared_semantic_core",
    "representation_contract",
    "grounding_identity",
    "claim_boundary",
    "scope_exclusions",
)

_CLASSIFICATION_SEVERITY = (
    "BLOCKING_MISMATCH",
    "INTENTIONAL_MIGRATION_REVIEW_REQUIRED",
    "NOT_YET_COMPARABLE",
    "UNSUPPORTED_BOTH",
    "EQUIVALENT",
)


def compare_identity_dimensions(
    identity: str,
    old_identity: dict[str, Any] | None,
    new_identity: dict[str, Any] | None,
) -> dict[str, Any]:
    """Assemble every static comparison dimension for one identity."""
    dimensions = {
        "declared_semantic_core": compare_declared(
            identity, old_identity, new_identity
        ),
        "representation_contract": compare_representation_contract(
            identity, old_identity, new_identity
        ),
        "grounding_identity": compare_grounding_identity(
            identity, old_identity, new_identity
        ),
        "claim_boundary": compare_claim_boundary(identity, old_identity, new_identity),
        "scope_exclusions": compare_scope_exclusions(
            identity, old_identity, new_identity
        ),
    }
    classifications = {
        name: value["classification"] for name, value in dimensions.items()
    }
    overall = next(
        classification
        for classification in _CLASSIFICATION_SEVERITY
        if classification in classifications.values()
    )
    return {
        "dimensions": dimensions,
        "classifications": classifications,
        "overall_static": overall,
    }


# ---------------------------------------------------------------------------
# Reviewed contract checks over the new-bundle chain
# ---------------------------------------------------------------------------


def _row_text(entry: dict[str, Any]) -> str:
    return json.dumps(entry["row"], sort_keys=True)


def _find_keys(value: Any, needle_keys: frozenset[str]) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in needle_keys:
                found.append(key)
            found.extend(_find_keys(item, needle_keys))
    elif isinstance(value, list):
        for item in value:
            found.extend(_find_keys(item, needle_keys))
    return found


_FORBIDDEN_PROMOTION_KEYS = frozenset(
    {
        "realizedBy",
        "allocatedTo",
        "deployedTo",
        "specifiesFunction",
        "satisfaction",
        "execution_success",
        "acceptance_claim",
    }
)


def run_contract_checks(chain: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Deterministic reviewed-contract checks over the new-bundle chain."""
    rows = chain_rows(chain)
    profiles = chain_profile_entries(chain)
    checks: list[dict[str, Any]] = []

    def record(check: str, identity: str, ok: bool, detail: str) -> None:
        checks.append(
            {
                "check": check,
                "identity": identity,
                "result": "PASS" if ok else "FAIL",
                "detail": detail,
            }
        )

    def row(identity: str) -> dict[str, Any]:
        return rows[identity]["row"]

    def relation(identity: str) -> dict[str, Any]:
        return row(identity)["relation"]

    # K pair integrity: one modeled fact / two navigations.
    pair = [relation(name) for name in K_PAIR]
    omf = [item.get("one_modeled_fact_two_navigations") or {} for item in pair]
    record(
        "k-pair-companion-linkage",
        "|".join(K_PAIR),
        omf[0].get("companion_predicate") == K_PAIR[1]
        and omf[1].get("companion_predicate") == K_PAIR[0],
        f"companions: {omf[0].get('companion_predicate')!r} / "
        f"{omf[1].get('companion_predicate')!r}",
    )
    record(
        "k-pair-one-witness",
        "|".join(K_PAIR),
        omf[0].get("witness") == omf[1].get("witness")
        and omf[0].get("witness_population") == omf[1].get("witness_population"),
        "identical witness + witness population statement",
    )
    record(
        "k-pair-native-direction",
        "|".join(K_PAIR),
        all(item.get("native_modeled_direction") == K_NATIVE_DIRECTION for item in pair),
        f"native_modeled_direction == {K_NATIVE_DIRECTION!r} on both",
    )
    directions = {str(item.get("canonical_direction") or "") for item in pair}
    record(
        "k-pair-inverse-directions",
        "|".join(K_PAIR),
        directions == {"Requirement -> Need", "Need -> Requirement"},
        f"canonical directions: {sorted(directions)}",
    )
    record(
        "k-pair-claim-boundary",
        "|".join(K_PAIR),
        all(
            all(fragment in str(item.get("claim_boundary") or "") for fragment in K_CLAIM_REQUIRED)
            for item in pair
        ),
        "provenance-only boundary on both navigations",
    )
    record(
        "k-pair-strength",
        "|".join(K_PAIR),
        all(str(item.get("semantic_strength")) == "derivation" for item in pair),
        "semantic_strength == derivation on both",
    )

    # hasSubject: both governed lineage restrictions, native-reference only.
    subject = relation("hasSubject")
    axes = {
        str(item.get("axis") or "")
        for item in subject.get("scope_restrictions", [])
        if isinstance(item, dict)
    }
    record(
        "hassubject-restrictions",
        "hasSubject",
        axes == {"source", "target"}
        and str(subject.get("semantic_strength")) == "native-reference"
        and str((subject.get("range") or {}).get("ontology_class")) == "MemberProduct",
        f"axes={sorted(axes)} strength={subject.get('semantic_strength')!r}",
    )

    # verifiedBy: Requirement -> VerificationCase, coverage semantics only.
    verified = relation("verifiedBy")
    verified_axes = {
        str(item.get("axis") or "")
        for item in verified.get("scope_restrictions", [])
        if isinstance(item, dict)
    }
    record(
        "verifiedby-coverage-only",
        "verifiedBy",
        str(verified.get("semantic_strength")) == "native-verification"
        and str((verified.get("range") or {}).get("ontology_class")) == "VerificationCase"
        and "source" in verified_axes
        and "coverage relation only"
        in str((verified.get("native_grounding") or {}).get("note") or ""),
        f"strength={verified.get('semantic_strength')!r} axes={sorted(verified_axes)}",
    )

    # hasRelevantArchitecture: bounded relevance, no fabricated binding.
    relevant = relation("hasRelevantArchitecture")
    exclusion = relevant.get("exclusion_lineage") or {}
    relevant_note = str((relevant.get("native_grounding") or {}).get("note") or "")
    range_note = str((relevant.get("range") or {}).get("note") or "")
    record(
        "hasrelevantarchitecture-bounded",
        "hasRelevantArchitecture",
        str(relevant.get("semantic_strength")) == "relevance"
        and str(exclusion.get("ontology_class")) == "MemberProduct"
        and "by itself is NOT hasRelevantArchitecture" in relevant_note
        and "no single file/declaration kernel binding" in range_note,
        "relevance strength + MemberProduct exclusion + no fabricated binding",
    )

    # No promotion keys anywhere in the scope rows.
    for identity in O3_SCOPE_IDENTITIES:
        found = _find_keys(row(identity), _FORBIDDEN_PROMOTION_KEYS)
        record(
            "no-promotion-keys",
            identity,
            not found,
            f"forbidden keys found: {sorted(set(found))}" if found else "clean",
        )

    # Projection/profile separation + semantic-contract echo consistency.
    for identity in O3_SCOPE_IDENTITIES:
        text = _row_text(rows[identity])
        leaked = [name for name in PROFILE_ONLY_MECHANICS if f'"{name}"' in text]
        record(
            "projection-mechanics-free",
            identity,
            not leaked,
            f"leaked mechanics: {leaked}" if leaked else "clean",
        )
        entry = profiles.get(identity)
        if entry is None:
            continue
        echo = entry["entry"].get("semantic_contract_echo") or {}
        if echo:
            declared = (
                row(identity).get("relation") if identity in O3_SCOPE_RELATIONSHIPS else None
            )
            if isinstance(declared, dict):
                ok = (
                    str(echo.get("domain")) == str((declared.get("domain") or {}).get("ontology_class"))
                    and str(echo.get("range")) == str((declared.get("range") or {}).get("ontology_class"))
                    and str(echo.get("canonical_direction")) == str(declared.get("canonical_direction"))
                    and str(echo.get("semantic_strength")) == str(declared.get("semantic_strength"))
                )
                record(
                    "profile-contract-echo",
                    identity,
                    ok,
                    "echo matches projection declaration"
                    if ok
                    else f"echo drift: {json.dumps(echo, sort_keys=True)[:200]}",
                )

    # Support-state honesty: every scope row stays vocabulary-only.
    for identity in O3_SCOPE_IDENTITIES:
        state = str(row(identity).get("support_state") or "")
        record(
            "support-state-vocabulary-only",
            identity,
            state == "vocabulary-only",
            f"support_state={state!r}",
        )

    # Reviewed exclusions are never emitted by the chain.
    emitted = set(rows)
    for identity in EXCLUDED_IDENTITIES:
        record(
            "excluded-identity-absent",
            identity,
            identity not in emitted,
            "absent from the O2 chain" if identity not in emitted else "EMITTED",
        )

    return checks


def check_support_preservation(
    old_bundle: dict[str, Any], new_bundle: dict[str, Any]
) -> list[dict[str, Any]]:
    """Support-state preservation matrix (old runtime gap vs new state)."""
    matrix: list[dict[str, Any]] = []
    for identity in O3_SCOPE_IDENTITIES:
        old_identity = old_bundle["identities"][identity]
        new_identity = new_bundle["identities"][identity]
        old_status = old_identity["runtime_status"]
        if old_identity["kind"] == "relationship":
            if old_status["blocked"]:
                old_support = "runtime-blocked"
            elif old_status["queryable_as_predicate"]:
                old_support = "runtime-queryable"
            else:
                old_support = "runtime-external"
        else:
            old_support = (
                "runtime-binding-identity"
                if old_identity["declared"]["kernel_mapping_kind"] == "file"
                else f"runtime-{old_identity['declared']['kernel_mapping_kind']}-vocabulary"
            )
        matrix.append(
            {
                "identity": identity,
                "old_runtime_support": old_support,
                "new_support_state": new_identity["support_state"],
                "promotion": "none",
                "readiness_verdict": "NO_PROMOTION",
                "runtime_preservation": "NOT_YET_COMPARABLE",
                "cutover_requirement": (
                    "the O3 runtime must preserve the old path's exact "
                    "queryable/blocked behavior for this identity; runtime "
                    "preservation remains part of the future same-revision "
                    "execution comparison, and publication or vocabulary "
                    "presence is never support promotion"
                ),
            }
        )
    return matrix


# ---------------------------------------------------------------------------
# Same-revision comparison harness (the future cutover's executable contract)
# ---------------------------------------------------------------------------

COMPARISON_MANIFEST_SCHEMA = "de4sdv.o3-comparison-manifest/v1"

#: Result fields compared as canonical SETS (ordering semantically irrelevant).
SET_FIELDS = (
    "targets",
    "witnesses",
    "nodes",
    "diagnostics",
    "unsupported_predicates",
)

#: Ordered fields where SysML ordering is semantically meaningful (a trace
#: path is a sequence; reordering it changes the engineering claim).
ORDERED_FIELDS = ("path",)


def validate_manifest_pair(
    old_manifest: dict[str, Any], new_manifest: dict[str, Any]
) -> list[str]:
    """Same-revision comparison contract: the ONLY intended variable is the
    authority path. Any basis difference blocks the comparison."""
    errors: list[str] = []
    for manifest in (old_manifest, new_manifest):
        if manifest.get("schema") != COMPARISON_MANIFEST_SCHEMA:
            errors.append(f"manifest-schema:{manifest.get('schema')!r}")
    for field_name in (
        "git_revision",
        "sysml_project_id",
        "sysml_commit_id",
        "import_closure_digest",
        "subject_ids",
        "evaluation_scope",
        "runtime_build",
        "completeness_boundary",
    ):
        old_value = old_manifest.get(field_name)
        new_value = new_manifest.get(field_name)
        if old_value != new_value:
            errors.append(f"basis-mismatch:{field_name}")
    if old_manifest.get("authority_path") == new_manifest.get("authority_path"):
        errors.append("authority-path-not-distinct")
    return errors


def _canonicalize(value: Any, *, ordered: bool) -> Any:
    if isinstance(value, list):
        if ordered:
            return value
        try:
            return sorted(value, key=lambda item: json.dumps(item, sort_keys=True))
        except TypeError:
            return sorted(str(item) for item in value)
    return value


def compare_semantic_results(
    old_result: dict[str, Any], new_result: dict[str, Any]
) -> dict[str, Any]:
    """Compare two query results produced over the SAME engineering inputs.

    The only intended variable is the authority path (old vs proposed new).
    Any basis difference blocks; any semantic difference blocks; ordering
    differences canonicalize only where declared semantically irrelevant
    (SET_FIELDS) — trace paths stay ordered.
    """
    mismatches: list[str] = []
    if old_result.get("source_revision") != new_result.get("source_revision"):
        mismatches.append("basis-mismatch:revision")
    if old_result.get("sysml_project_id") != new_result.get("sysml_project_id"):
        mismatches.append("basis-mismatch:sysml-project")
    if old_result.get("sysml_commit_id") != new_result.get("sysml_commit_id"):
        mismatches.append("basis-mismatch:sysml-commit")
    if old_result.get("predicate") != new_result.get("predicate"):
        mismatches.append("predicate-mismatch")
    if old_result.get("subject_id") != new_result.get("subject_id"):
        mismatches.append("subject-mismatch")
    if old_result.get("direction") != new_result.get("direction"):
        mismatches.append("canonical-direction-mismatch")
    if old_result.get("semantic_strength") != new_result.get("semantic_strength"):
        mismatches.append("semantic-strength-mismatch")
    if old_result.get("claim_boundary") != new_result.get("claim_boundary"):
        mismatches.append("claim-boundary-mismatch")
    if old_result.get("support_state") != new_result.get("support_state"):
        mismatches.append("support-state-mismatch")
    if old_result.get("completeness") != new_result.get("completeness"):
        mismatches.append("completeness-mismatch")
    if old_result.get("unsupported") != new_result.get("unsupported"):
        mismatches.append("unsupported-state-mismatch")

    compared_fields: dict[str, dict[str, Any]] = {}
    for field_name in SET_FIELDS + ORDERED_FIELDS:
        if field_name not in old_result and field_name not in new_result:
            continue
        ordered = field_name in ORDERED_FIELDS
        old_value = _canonicalize(old_result.get(field_name), ordered=ordered)
        new_value = _canonicalize(new_result.get(field_name), ordered=ordered)
        ok = old_value == new_value
        compared_fields[field_name] = {"old": old_value, "new": new_value, "ok": ok}
        if not ok:
            mismatches.append(f"{field_name}-mismatch")

    return {
        "classification": "EQUIVALENT" if not mismatches else "BLOCKING_MISMATCH",
        "mismatches": mismatches,
        "fields": compared_fields,
    }


def check_k_pair_witness_consistency(
    old_navigations: dict[str, dict[str, Any]],
    new_navigations: dict[str, dict[str, Any]],
) -> list[str]:
    """The K pair must remain one modeled fact under both authority paths.

    ``*_navigations`` map the two predicate names to result dicts whose
    ``witnesses`` are the witness element ids. The new path must not
    materialize two independent facts where the old path shares one.
    """
    errors: list[str] = []
    redirect, forward = K_PAIR
    for label, navigations in (("old", old_navigations), ("new", new_navigations)):
        for name in K_PAIR:
            if name not in navigations:
                errors.append(f"{label}-missing-navigation:{name}")
    if errors:
        return errors
    old_shared = set(old_navigations[redirect].get("witnesses") or []) == set(
        old_navigations[forward].get("witnesses") or []
    )
    new_shared = set(new_navigations[redirect].get("witnesses") or []) == set(
        new_navigations[forward].get("witnesses") or []
    )
    if not old_shared:
        errors.append("old-path-witness-identity-broken")
    if not new_shared:
        errors.append("k-pair-duplication:new-path-materializes-independent-facts")
    if old_shared and new_shared:
        if set(new_navigations[redirect].get("witnesses") or []) != set(
            old_navigations[redirect].get("witnesses") or []
        ):
            errors.append("k-pair-witness-population-mismatch")
    return errors


# ---------------------------------------------------------------------------
# Scope document assembly, checking, and the write guard
# ---------------------------------------------------------------------------


def assert_writable(path: Path, root: Path) -> None:
    """The companion CLI may write exactly one repository path, ever."""
    allowed = (root / O3_SCOPE_PATH).resolve()
    if path.resolve() != allowed:
        raise ValueError(
            f"refusing to write {path}: the O3 readiness tooling may only "
            f"write {O3_SCOPE_PATH}"
        )


def build_scope_document(root: Path) -> dict[str, Any]:
    """Assemble the full machine-readable O3 equivalence scope document."""
    contract = KernelContract.load(root / ONTOLOGY_PATH)
    chain = load_o2_chain(root)
    old_bundle = extract_old_bundle(root, contract)
    new_bundle = extract_new_bundle(chain)
    identities: list[dict[str, Any]] = []
    for identity in O3_SCOPE_IDENTITIES:
        comparison = compare_identity_dimensions(
            identity,
            old_bundle["identities"].get(identity),
            new_bundle["identities"].get(identity),
        )
        identities.append(
            {
                "identity": identity,
                "kind": old_bundle["identities"][identity]["kind"],
                "o2_source": new_bundle["identities"][identity]["o2_artifact"],
                "old_authority": old_bundle["identities"][identity],
                "new_authority": new_bundle["identities"][identity],
                "comparison": comparison,
                "runtime_behavior": {
                    "classification": "NOT_YET_COMPARABLE",
                    "reason": (
                        "the new authority path has no runtime implementation "
                        "at readiness; the O3 cutover must execute the "
                        "same-revision comparison harness before any "
                        "activation claim"
                    ),
                    "required_harness": COMPARISON_MANIFEST_SCHEMA,
                },
            }
        )
    contract_checks = run_contract_checks(chain)
    support_matrix = check_support_preservation(old_bundle, new_bundle)
    basis = {
        "ontology": old_bundle["ontology"],
        "kernel_contract_module": old_bundle["kernel_contract_module"],
        "kernel_contract_identity": old_bundle["kernel_contract_identity"],
        "runtime_files": old_bundle["runtime_files"],
        "o2_chain": new_bundle["chain"],
    }
    inventory_path = root / O1_INVENTORY_PATH
    if inventory_path.exists():
        basis["o1_inventory"] = {
            "path": O1_INVENTORY_PATH,
            "sha256": sha256_file(inventory_path),
        }
    return {
        "schema": O3_SCOPE_SCHEMA,
        "generated_by": "scripts/generate_o3_equivalence_scope.py",
        "read_only": True,
        "note": (
            "Planning/evidence for the O3 authority transition. This document "
            "is NOT activation authority: no runtime authority is switched, "
            "no YAML is retired, and no support state is promoted by its "
            "existence. Static parity is compared per identity across "
            "separate dimensions (declared semantic core, representation "
            "contract, grounding identity, claim boundary, scope/exclusions); "
            "any static mismatch fails closed, and an identity is never "
            "EQUIVALENT merely because its semantic core matches. "
            "Runtime-behavior equivalence remains NOT_YET_COMPARABLE until "
            "the same-revision comparison harness runs at cutover over an "
            "exact-revision validated ingestion."
        ),
        "basis": {
            **basis,
            "comparison_base_revision": resolve_comparison_base_revision(root),
            "comparison_base_policy": BASE_REVISION_POLICY,
        },
        "scope": {
            "reviewed_surface_count": len(O3_SCOPE_IDENTITIES),
            "o2_1": list(O2_SURFACE_O21),
            "o2_2": list(O2_SURFACE_O22),
            "o2_3": list(O2_SURFACE_O23),
            "excluded_identities": list(EXCLUDED_IDENTITIES),
        },
        "identities": identities,
        "contract_checks": contract_checks,
        "support_preservation": support_matrix,
        "summary": {
            "static_parity": {
                "dimensions": {
                    dimension: {
                        "equivalent": sorted(
                            item["identity"]
                            for item in identities
                            if item["comparison"]["classifications"][dimension]
                            == "EQUIVALENT"
                        ),
                        "not_yet_comparable": sorted(
                            item["identity"]
                            for item in identities
                            if item["comparison"]["classifications"][dimension]
                            == "NOT_YET_COMPARABLE"
                        ),
                        "mismatch": sorted(
                            item["identity"]
                            for item in identities
                            if item["comparison"]["classifications"][dimension]
                            not in ("EQUIVALENT", "NOT_YET_COMPARABLE")
                        ),
                    }
                    for dimension in COMPARISON_DIMENSIONS
                },
                "identities_fully_equivalent": sorted(
                    item["identity"]
                    for item in identities
                    if item["comparison"]["overall_static"] == "EQUIVALENT"
                ),
                "identities_with_mismatch": sorted(
                    item["identity"]
                    for item in identities
                    if item["comparison"]["overall_static"]
                    not in ("EQUIVALENT", "NOT_YET_COMPARABLE")
                ),
                "identities_with_pending_dimension": sorted(
                    item["identity"]
                    for item in identities
                    if item["comparison"]["overall_static"] == "NOT_YET_COMPARABLE"
                ),
            },
            "runtime": {
                "completed": [],
                "equivalent": [],
                "not_yet_comparable": sorted(
                    item["identity"] for item in identities
                ),
            },
            "contract_check_failures": sorted(
                check["check"] + ":" + check["identity"]
                for check in contract_checks
                if check["result"] != "PASS"
            ),
        },
    }


def check_scope_document(root: Path, document: dict[str, Any]) -> list[str]:
    """Fail-closed validation of the committed scope document."""
    errors: list[str] = []
    if document.get("schema") != O3_SCOPE_SCHEMA:
        return [f"scope schema mismatch: {document.get('schema')!r}"]
    expected = build_scope_document(root)

    # The comparison-base revision is validated (existence + ancestry), not
    # byte-compared: regeneration legitimately resolves the then-current
    # permanent main revision, which can only ever move FORWARD on main.
    recorded_revision = str(
        (document.get("basis") or {}).get("comparison_base_revision") or ""
    )
    recorded = dict(document)
    regenerated = dict(expected)
    for candidate in (recorded, regenerated):
        basis = dict(candidate.get("basis") or {})
        basis.pop("comparison_base_revision", None)
        candidate["basis"] = basis
    if canonical_json(recorded) != canonical_json(regenerated):
        errors.append(
            "scope document differs from regeneration: regenerate "
            f"{O3_SCOPE_PATH} (digest drift or unrecorded change)"
        )
    if not recorded_revision:
        errors.append("scope document records no comparison base revision")
    else:
        try:
            _git(root, "cat-file", "-e", f"{recorded_revision}^{{commit}}")
            _git(root, "merge-base", "--is-ancestor", recorded_revision, "HEAD")
        except ValueError as exc:
            errors.append(
                "comparison base revision is not a valid ancestor of the "
                f"checked-out revision: {exc}"
            )
    for item in expected["identities"]:
        for dimension, report in item["comparison"]["dimensions"].items():
            if report["classification"] in (
                "BLOCKING_MISMATCH",
                "INTENTIONAL_MIGRATION_REVIEW_REQUIRED",
                "UNSUPPORTED_BOTH",
            ):
                errors.append(
                    f"static mismatch for {item['identity']} ({dimension}): "
                    f"{report.get('reasons')}"
                )
    for check in expected["contract_checks"]:
        if check["result"] != "PASS":
            errors.append(
                f"contract check failed: {check['check']} ({check['identity']}): "
                f"{check['detail']}"
            )
    return errors


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"
