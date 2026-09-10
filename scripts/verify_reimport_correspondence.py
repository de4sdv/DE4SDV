#!/usr/bin/env python3
"""MC-14: correspondence across two INDEPENDENT serialization/import transactions.

The frozen contract requires correspondence evidence that does not assume UUID
reuse: two independent export transactions of the same committed source are
imported into two distinct API revisions, then compared. Raw API UUID equality
is neither required nor assumed; correspondence is established from stable
explicit identities (declared short name / declared name, with the API metaclass
as a type constraint) plus the semantic relationships reachable from each
identity. Name merging, duplicate identities and contradictory pairs fail
closed.

Each UUID in the report is attributed to the transaction it came from.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.relationships import build_relationship_graph  # noqa: E402
from de4sdv.sysml_api.client import ApiClient  # noqa: E402
from de4sdv.sysml_api.repository import SysMLRepository  # noqa: E402
from de4sdv.sysml_api.revisions import RevisionBinding  # noqa: E402

SCHEMA = "de4sdv-reimport-correspondence/v1"


def _explicit_key(element: dict[str, Any]) -> str | None:
    short = str(element.get("declaredShortName") or "").strip()
    if short:
        return short
    name = str(element.get("declaredName") or "").strip()
    return name or None


def _inventory(
    elements: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Explicit-identity inventory; duplicates are a fail-closed condition."""
    inventory: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []
    for element in elements:
        key = _explicit_key(element)
        if key is None:
            continue
        if key in inventory:
            duplicates.append(key)
            continue
        inventory[key] = element
    return inventory, sorted(set(duplicates))


def _edge_signature(
    graph, key: str, element: dict[str, Any], inventory: dict[str, dict[str, Any]]
) -> list[list[str]]:
    """Relationship signature in explicit-identity space."""
    reverse = {
        str(item["@id"]): item_key
        for item_key, item in inventory.items()
        if item.get("@id")
    }
    element_id_value = str(element.get("@id") or "")
    signature = []
    for hop in graph.outgoing(element_id_value):
        target_key = reverse.get(hop.target)
        if target_key is None:
            continue
        signature.append([hop.kind, target_key])
    return sorted(signature)


def verify(
    api_url: str,
    binding_a_path: Path,
    binding_b_path: Path,
    label_a: str = "transaction-a",
    label_b: str = "transaction-b",
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

    inventory_a, duplicates_a = _inventory(elements_a)
    inventory_b, duplicates_b = _inventory(elements_b)
    for key in duplicates_a:
        failures.append(f"{label_a}: duplicate explicit identity {key!r}")
    for key in duplicates_b:
        failures.append(f"{label_b}: duplicate explicit identity {key!r}")

    graph_a = build_relationship_graph(elements_a)
    graph_b = build_relationship_graph(elements_b)

    only_a = sorted(set(inventory_a) - set(inventory_b))
    only_b = sorted(set(inventory_b) - set(inventory_a))
    for key in only_a:
        failures.append(f"identity present only in {label_a}: {key!r}")
    for key in only_b:
        failures.append(f"identity present only in {label_b}: {key!r}")

    per_identity: list[dict[str, Any]] = []
    uuid_equal = 0
    uuid_differing = 0
    relationship_mismatches: list[str] = []
    for key in sorted(set(inventory_a) & set(inventory_b)):
        element_a = inventory_a[key]
        element_b = inventory_b[key]
        uuid_a = str(element_a.get("@id") or "")
        uuid_b = str(element_b.get("@id") or "")
        equal = bool(uuid_a) and uuid_a == uuid_b
        uuid_equal += int(equal)
        uuid_differing += int(not equal)
        name_a = str(element_a.get("declaredName") or "")
        name_b = str(element_b.get("declaredName") or "")
        metaclass_a = str(element_a.get("@type") or "")
        metaclass_b = str(element_b.get("@type") or "")
        if name_a != name_b:
            failures.append(
                f"{key!r}: declared name differs across transactions "
                f"({label_a}={name_a!r}, {label_b}={name_b!r})"
            )
        if metaclass_a != metaclass_b:
            failures.append(
                f"{key!r}: API metaclass differs across transactions "
                f"({label_a}={metaclass_a!r}, {label_b}={metaclass_b!r})"
            )
        signature_a = _edge_signature(graph_a, key, element_a, inventory_a)
        signature_b = _edge_signature(graph_b, key, element_b, inventory_b)
        relationships_match = signature_a == signature_b
        if not relationships_match:
            relationship_mismatches.append(key)
            failures.append(
                f"{key!r}: semantic relationships differ across transactions"
            )
        per_identity.append(
            {
                "identity": key,
                "declared_name": name_a,
                "metaclass": metaclass_a,
                "uuid_by_transaction": {label_a: uuid_a, label_b: uuid_b},
                "uuid_equal": equal,
                "relationships_match": relationships_match,
                "relationship_count": len(signature_a),
            }
        )

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "passed": not failures,
        "failures": failures,
        "correspondence": {
            "method": "explicit-identity-v1",
            "uuid_reuse_assumed": False,
            "uuid_equality_required": False,
            "name_merge_used": False,
        },
        "transactions": {
            label_a: {
                "api_project_id": binding_a.sysml_project_id,
                "api_commit_id": binding_a.sysml_commit_id,
                "git_commit": binding_a.git_commit,
                "scope": binding_a.scope,
                "import_timestamp": binding_a.import_timestamp,
                "element_count": len(elements_a),
                "explicit_identity_count": len(inventory_a),
            },
            label_b: {
                "api_project_id": binding_b.sysml_project_id,
                "api_commit_id": binding_b.sysml_commit_id,
                "git_commit": binding_b.git_commit,
                "scope": binding_b.scope,
                "import_timestamp": binding_b.import_timestamp,
                "element_count": len(elements_b),
                "explicit_identity_count": len(inventory_b),
            },
        },
        "uuid_attribution": {
            "identical_uuids": uuid_equal,
            "differing_uuids": uuid_differing,
            "note": (
                "UUID equality is reported, never required. Correspondence was "
                "established from explicit identities and relationship "
                "structure; each UUID above is attributed to its transaction."
            ),
        },
        "identities_compared": len(per_identity),
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
        f"correspondence verified across {report['identities_compared']} explicit "
        f"identities ({report['uuid_attribution']['identical_uuids']} identical "
        f"UUIDs, {report['uuid_attribution']['differing_uuids']} differing)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
