#!/usr/bin/env python3
"""MC-14 / UG-03: correspondence across two INDEPENDENT serialization/import transactions.

The frozen contract and the v1.1 plan require PERSISTENT-ID correspondence:
two independent export transactions of the same committed source are imported
into two distinct API revisions and compared using stable explicit identities
(the model-authored persistent short identity, ``declaredShortName``) only.

Rules enforced here:

- ``declaredName`` NEVER establishes correspondence and is never used as a
  fallback key. Names are compared only as attributes, after identity has
  been established.
- Duplicate or missing persistent identities never silently fall back to
  names; duplicates fail closed, and every identity required by the Lane B
  pilot contract must be present with a persistent identity in BOTH
  transactions.
- Raw API UUID equality is neither required nor assumed; UUIDs are reported
  per transaction (``uuid_by_transaction``) and attributed accordingly.
- Semantic relationship structure is compared using the persistent
  identities of semantic endpoints where available, plus relationship
  kind/metaclass, endpoint metaclass, and explicit/implied provenance.
  Serializer-internal anonymous witness objects (no persistent identity) are
  matched structurally as part of an already-corresponded witness path; they
  are never globally merged by name.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.relationships import build_relationship_graph  # noqa: E402
from de4sdv.sysml_api.client import ApiClient  # noqa: E402
from de4sdv.sysml_api.repository import SysMLRepository  # noqa: E402
from de4sdv.sysml_api.revisions import RevisionBinding  # noqa: E402

SCHEMA = "de4sdv-reimport-correspondence/v1"

#: The persistent-identity mechanism: the model-authored declared short name
#: (the same stable explicit identity the pilot contract selects subjects by).
PERSISTENT_IDENTITY_FIELD = "declaredShortName"

#: Identities the Lane B pilot contract requires in every candidate revision.
REQUIRED_PILOT_IDENTITIES: tuple[str, ...] = (
    "VC-AEBS-009D-DE",
    "VC-AEBS-009D-01",
    "VC-AEBS-009D-02",
    "VC-AEBS-009D-03",
    "VC-AEBS-009D-04",
    "VC-AEBS-009D-05",
    "VC-AEBS-009D-06",
    "EC-009D-01",
    "EC-009D-02",
    "EC-009D-03",
    "PSC-009D",
)


def _persistent_key(element: dict[str, Any]) -> str | None:
    """The element's persistent explicit identity, or None.

    ``declaredShortName`` only — deliberately NO ``declaredName`` fallback:
    names must never establish identity across transactions.
    """
    short = str(element.get(PERSISTENT_IDENTITY_FIELD) or "").strip()
    return short or None


def _inventory(
    elements: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, int], int]:
    """Persistent-identity inventory.

    Returns (inventory, ambiguous, count of elements without a persistent
    identity).

    An identity is AMBIGUOUS when multiple elements in the same transaction
    carry the same ``declaredShortName`` (legal SysML across namespaces —
    the pinned upstream libraries use per-view short names such as ``soi``).
    Ambiguous identities are excluded from the global correspondence
    key-space and recorded with their occurrence counts: they are never
    matched arbitrarily and never recovered by name. Required pilot
    identities are checked separately against both missing and ambiguous
    cases and fail closed.
    """
    counts: dict[str, int] = {}
    first: dict[str, dict[str, Any]] = {}
    without_identity = 0
    for element in elements:
        key = _persistent_key(element)
        if key is None:
            without_identity += 1
            continue
        counts[key] = counts.get(key, 0) + 1
        first.setdefault(key, element)
    ambiguous = {key: count for key, count in counts.items() if count > 1}
    inventory = {
        key: element for key, element in first.items() if counts[key] == 1
    }
    return inventory, ambiguous, without_identity


def _edge_signature(
    graph, element: dict[str, Any], inventory: dict[str, dict[str, Any]]
) -> list[list[str]]:
    """Semantic relationship signature in persistent-identity space.

    Each row is [relationship kind, provenance, endpoint metaclass,
    endpoint persistent identity or "<anonymous>"]. Anonymous serializer
    witness targets are matched structurally (kind + metaclass + provenance
    + path position via multiset) inside this already-corresponded witness
    path; they are never merged globally by name.
    """
    reverse = {
        str(item["@id"]): item_key
        for item_key, item in inventory.items()
        if item.get("@id")
    }
    element_id_value = str(element.get("@id") or "")
    signature = []
    for hop in graph.outgoing(element_id_value):
        target_key = reverse.get(hop.target)
        target_element = graph.element(hop.target) or {}
        target_metaclass = str(target_element.get("@type") or "")
        signature.append(
            [
                hop.kind,
                hop.provenance,
                target_metaclass,
                target_key if target_key is not None else "<anonymous>",
            ]
        )
    return sorted(signature)


def verify(
    api_url: str,
    binding_a_path: Path,
    binding_b_path: Path,
    label_a: str = "transaction-a",
    label_b: str = "transaction-b",
    required_identities: Iterable[str] = REQUIRED_PILOT_IDENTITIES,
) -> dict[str, Any]:
    binding_a = RevisionBinding.from_dict(json.loads(binding_a_path.read_text()))
    binding_b = RevisionBinding.from_dict(json.loads(binding_b_path.read_text()))
    repository = SysMLRepository(ApiClient(api_url, timeout=600.0))
    elements_a = repository.list_elements(
        binding_a.sysml_project_id, binding_a.sysml_commit_id
    )
    elements_b = repository.list_elements(
        binding_b.sysml_project_id, binding_b.sysml_commit_id
    )
    failures: list[str] = []
    if not elements_a or not elements_b:
        failures.append("one or both transactions produced an empty element listing")
    if binding_a.sysml_project_id == binding_b.sysml_project_id:
        failures.append(
            "both bindings reference the same API project: not independent transactions"
        )
    if binding_a.sysml_commit_id == binding_b.sysml_commit_id:
        failures.append(
            "both bindings reference the same API commit: not independent transactions"
        )

    inventory_a, ambiguous_a, anonymous_a = _inventory(elements_a)
    inventory_b, ambiguous_b, anonymous_b = _inventory(elements_b)

    graph_a = build_relationship_graph(elements_a)
    graph_b = build_relationship_graph(elements_b)

    required = sorted(set(required_identities))

    def _required_problem(key: str, label: str, inventory: dict, ambiguous: dict) -> str | None:
        if key in ambiguous:
            return (
                f"required pilot identity {key!r} is ambiguous in {label}: "
                f"{ambiguous[key]} elements share this short name "
                "(excluded from correspondence; must resolve uniquely)"
            )
        if key not in inventory:
            return (
                f"required pilot identity {key!r} has no persistent identity in {label}"
            )
        return None

    missing_required_a = [
        key for key in required if (problem := _required_problem(key, label_a, inventory_a, ambiguous_a))
    ]
    missing_required_b = [
        key for key in required if (problem := _required_problem(key, label_b, inventory_b, ambiguous_b))
    ]
    for key in missing_required_a:
        failures.append(_required_problem(key, label_a, inventory_a, ambiguous_a) or "")
    for key in missing_required_b:
        failures.append(_required_problem(key, label_b, inventory_b, ambiguous_b) or "")

    # Global correspondence key-space: persistent identities only. Elements
    # without a persistent identity are never matched by name (they may only
    # participate structurally inside an already-corresponded witness path).
    only_a = sorted(set(inventory_a) - set(inventory_b))
    only_b = sorted(set(inventory_b) - set(inventory_a))
    for key in only_a:
        failures.append(f"persistent identity present only in {label_a}: {key!r}")
    for key in only_b:
        failures.append(f"persistent identity present only in {label_b}: {key!r}")

    per_identity: list[dict[str, Any]] = []
    uuid_equal = 0
    uuid_differing = 0
    relationship_mismatches: list[str] = []
    name_attribute_mismatches: list[str] = []
    for key in sorted(set(inventory_a) & set(inventory_b)):
        element_a = inventory_a[key]
        element_b = inventory_b[key]
        uuid_a = str(element_a.get("@id") or "")
        uuid_b = str(element_b.get("@id") or "")
        equal = bool(uuid_a) and uuid_a == uuid_b
        uuid_equal += int(equal)
        uuid_differing += int(not equal)
        # Names are attributes, compared only AFTER identity is established.
        name_a = str(element_a.get("declaredName") or "")
        name_b = str(element_b.get("declaredName") or "")
        metaclass_a = str(element_a.get("@type") or "")
        metaclass_b = str(element_b.get("@type") or "")
        if name_a != name_b:
            name_attribute_mismatches.append(key)
            failures.append(
                f"{key!r}: declared-name attribute differs across transactions "
                f"({label_a}={name_a!r}, {label_b}={name_b!r})"
            )
        if metaclass_a != metaclass_b:
            failures.append(
                f"{key!r}: API metaclass differs across transactions "
                f"({label_a}={metaclass_a!r}, {label_b}={metaclass_b!r})"
            )
        signature_a = _edge_signature(graph_a, element_a, inventory_a)
        signature_b = _edge_signature(graph_b, element_b, inventory_b)
        relationships_match = signature_a == signature_b
        if not relationships_match:
            relationship_mismatches.append(key)
            failures.append(
                f"{key!r}: semantic relationship structure differs across transactions"
            )
        per_identity.append(
            {
                "identity": key,
                "identity_mechanism": PERSISTENT_IDENTITY_FIELD,
                "declared_name_attribute": name_a,
                "metaclass": metaclass_a,
                "uuid_by_transaction": {label_a: uuid_a, label_b: uuid_b},
                "uuid_equal": equal,
                "relationships_match": relationships_match,
                "relationship_count": len(signature_a),
                "anonymous_witness_targets": sum(
                    1 for row in signature_a if row[3] == "<anonymous>"
                ),
            }
        )

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "passed": not failures,
        "failures": failures,
        "correspondence": {
            "method": "persistent-explicit-identity-v1",
            "persistent_identity_field": PERSISTENT_IDENTITY_FIELD,
            "name_based_correspondence_used": False,
            "declared_name_used_as_identity_key": False,
            "declared_name_role": (
                "attribute comparison only, after identity is established; "
                "names never establish identity and are never a fallback key"
            ),
            "uuid_reuse_assumed": False,
            "uuid_equality_required": False,
            "anonymous_witness_policy": (
                "serializer-internal objects without a persistent identity are "
                "excluded from the global correspondence key-space and are "
                "matched structurally (relationship kind, endpoint metaclass, "
                "provenance, multiset position) inside an already-corresponded "
                "witness path only"
            ),
            "ambiguous_identity_policy": (
                "an identity is ambiguous when multiple elements in one "
                "transaction carry the same declaredShortName (legal across "
                "namespaces; the pinned upstream libraries reuse per-view short "
                "names). Ambiguous identities are excluded from global "
                "correspondence with recorded occurrence counts and are never "
                "matched arbitrarily; required pilot identities must resolve "
                "uniquely or the check fails closed"
            ),
        },
        "transactions": {
            label_a: {
                "api_project_id": binding_a.sysml_project_id,
                "api_commit_id": binding_a.sysml_commit_id,
                "git_commit": binding_a.git_commit,
                "scope": binding_a.scope,
                "import_timestamp": binding_a.import_timestamp,
                "element_count": len(elements_a),
                "persistent_identity_count": len(inventory_a),
                "elements_without_persistent_identity": anonymous_a,
            },
            label_b: {
                "api_project_id": binding_b.sysml_project_id,
                "api_commit_id": binding_b.sysml_commit_id,
                "git_commit": binding_b.git_commit,
                "scope": binding_b.scope,
                "import_timestamp": binding_b.import_timestamp,
                "element_count": len(elements_b),
                "persistent_identity_count": len(inventory_b),
                "elements_without_persistent_identity": anonymous_b,
            },
        },
        "uuid_attribution": {
            "identical_uuids": uuid_equal,
            "differing_uuids": uuid_differing,
            "note": (
                "UUID equality is reported, never required. Correspondence was "
                "established from persistent explicit identities and "
                "relationship structure; each UUID above is attributed to its "
                "transaction and no UUID-stability assumption is made."
            ),
        },
        "required_identities": {
            "count": len(required),
            "missing_in_" + label_a: missing_required_a,
            "missing_in_" + label_b: missing_required_b,
        },
        "ambiguous_persistent_identities": {
            label_a: ambiguous_a,
            label_b: ambiguous_b,
            "note": (
                "excluded from global correspondence; recorded for "
                "transparency, never matched by name"
            ),
        },
        "identities_compared": len(per_identity),
        "identities_compared_list": [row["identity"] for row in per_identity],
        "semantic_witness_equivalence": {
            "compared": len(per_identity),
            "matched": len(per_identity) - len(relationship_mismatches),
            "mismatched": len(relationship_mismatches),
            "mismatched_identities": relationship_mismatches,
        },
        "name_attribute_mismatches": name_attribute_mismatches,
        "relationship_mismatches": relationship_mismatches,
        "per_identity": per_identity,
        "source_commit_agreement": binding_a.git_commit == binding_b.git_commit,
    }
    if binding_a.git_commit != binding_b.git_commit:
        failures.append(
            "transactions were produced from different Git commits; MC-14 requires "
            "two transactions of the same committed source"
        )
        report["passed"] = False
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--binding-a", type=Path, required=True)
    parser.add_argument("--binding-b", type=Path, required=True)
    parser.add_argument("--label-a", default="transaction-a")
    parser.add_argument("--label-b", default="transaction-b")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = verify(
        args.api_url,
        args.binding_a,
        args.binding_b,
        label_a=args.label_a,
        label_b=args.label_b,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not report["passed"]:
        print(json.dumps(report, indent=2))
        return 1
    print(
        f"persistent-identity correspondence verified across "
        f"{report['identities_compared']} identities "
        f"({report['uuid_attribution']['identical_uuids']} identical UUIDs, "
        f"{report['uuid_attribution']['differing_uuids']} differing; "
        f"name-based correspondence used: false)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
