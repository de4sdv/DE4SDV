#!/usr/bin/env python3
"""Prove the derivesRequirementFromNeed slice against one validated API revision.

Loads the revision binding (including ingestion-validated kernel bindings),
assembles the existing semantic runtime, and queries the predicate for real
AEBS requirements. The proof asserts, per positive case:

- exactly the expected edge count;
- the exact expected source, target, and dependency witness UUIDs (resolved
  from the revision by declared case identity, then cross-checked);
- derivation strength, a complete discriminator witness (relationship +
  marker usage + annotation owner), and NO gaps (an incomplete-closure gap
  is never accepted as a pass); and
- inverse navigation (``derivedRequirementsOfNeed``) over the same witness
  from the need side, sharing witness identity with the forward edge.

Adversarial cases must return zero edges. Any exception during evaluation is
a failure, not a pass.

The expected Git revision is supplied independently via ``--expected-revision``
(or ``--expected-revision-file``); the script fails if the binding does not
match it, so a binding for a different candidate can never silently pass.

Usage:
    python scripts/prove_derivation_slice.py \\
        --api-url https://sysml-api.de4sdv.org \\
        --binding <binding.json> \\
        --expected-revision <full-40-hex-sha> \\
        [--output /tmp/derivation-proof.json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.runtime import build_semantic_runtime  # noqa: E402

POSITIVE_CASES: dict[str, dict[str, str]] = {
    # case name -> expected need (target) declared identity
    "reqDetectForwardCollisionRisk": {"need": "needCommonAEBSCapability"},
    "reqProvideCollisionWarning": {"need": "needCommonAEBSCapability"},
    "reqCommandEmergencyBraking": {"need": "needCommonAEBSCapability"},
    "reqPedestrianTargetResponse": {
        "need": "needPedestrianCollisionRiskReduction"
    },
    "reqBicycleTargetResponse": {
        "need": "needBicycleCollisionRiskReduction"
    },
}

ADVERSARIAL_CASES: tuple[str, ...] = (
    # RequirementUsage->RequirementUsage dependencies WITHOUT the marker
    # (relevance/trace edges): the predicate must not fire on endpoint
    # types alone.
    "reqAllowDriverOverride",
    "reqResistFalseReaction",
)

INVERSE_PREDICATE = "derivedRequirementsOfNeed"
FORWARD_PREDICATE = "derivesRequirementFromNeed"


def _resolve_case_element(service: Any, name: str, kind: str) -> str:
    """Resolve one declared case identity to its API UUID in the revision."""
    resolution = service.resolve_element(name)
    element_id = resolution["element"]["element_id"]
    if not element_id:
        raise AssertionError(f"{kind} {name!r} did not resolve to an API UUID")
    return str(element_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--binding", required=True, type=Path)
    parser.add_argument(
        "--expected-revision",
        default=None,
        help="full 40-hex Git SHA the candidate is expected to be bound to "
        "(independently supplied, never taken from the binding)",
    )
    parser.add_argument(
        "--expected-revision-file",
        type=Path,
        default=None,
        help="read the expected revision from this file (first token)",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    failures: list[str] = []

    binding = json.loads(args.binding.read_text(encoding="utf-8"))
    expected_revision = args.expected_revision
    if args.expected_revision_file is not None:
        expected_revision = (
            args.expected_revision_file.read_text(encoding="utf-8")
            .split()[0]
            .strip()
        )
    if not expected_revision:
        failures.append(
            "no independently supplied expected revision (--expected-revision "
            "or --expected-revision-file); refusing to take the candidate "
            "identity from the binding itself"
        )
    elif not re.fullmatch(r"[0-9a-f]{40}", str(expected_revision)):
        failures.append(
            f"expected revision {expected_revision!r} is not a full 40-hex SHA"
        )
    elif binding.get("git_commit") != expected_revision:
        failures.append(
            f"binding git_commit {binding.get('git_commit')!r} does not match "
            f"the independently supplied expected revision {expected_revision!r}"
        )
        expected_revision = None
    if failures:
        report = {
            "schema": "de4sdv-derivation-slice-proof/v2",
            "verdict": "fail",
            "failures": failures,
            "cases": [],
        }
        payload = json.dumps(report, indent=1, sort_keys=True)
        if args.output is not None:
            args.output.write_text(payload, encoding="utf-8")
        print(payload)
        return 1

    service = build_semantic_runtime(
        api_url=args.api_url,
        binding_path=args.binding,
        expected_git_revision=str(expected_revision),
        ontology_path=ROOT
        / "approach/framework/ontology/de4sdv-basic-ontology.yaml",
    )

    report: dict[str, object] = {
        "schema": "de4sdv-derivation-slice-proof/v2",
        "expected_revision": expected_revision,
        "revision": service._revision(),
        "cases": [],
    }

    # Positive cases: resolve the exact case identities from the revision,
    # then assert edge identity, strength, witness completeness, no gaps,
    # and inverse navigation over the same witness.
    for name, expectation in POSITIVE_CASES.items():
        case: dict[str, object] = {"case": name, "kind": "positive"}
        try:
            source_id = _resolve_case_element(service, name, "requirement")
            need_id = _resolve_case_element(service, expectation["need"], "need")
            result = service.semantic_neighbors(
                name, predicates=[FORWARD_PREDICATE]
            )
            edges = result["edges"]
            gaps = result["gaps"]
            case["source_id"] = source_id
            case["need_id"] = need_id
            case["edges"] = edges
            case["gaps"] = gaps
            if not edges:
                failures.append(
                    f"positive case {name} returned no derivation edge"
                )
            elif len(edges) != 1:
                failures.append(
                    f"positive case {name} returned {len(edges)} edges; "
                    f"expected exactly 1"
                )
            else:
                edge = edges[0]
                if gaps:
                    failures.append(
                        f"positive case {name} reported gaps {gaps!r}; an "
                        f"incomplete observation is never a pass"
                    )
                if edge["source"] != source_id:
                    failures.append(
                        f"positive case {name}: edge source {edge['source']!r} "
                        f"!= resolved requirement {source_id!r}"
                    )
                if edge["target"] != need_id:
                    failures.append(
                        f"positive case {name}: edge target {edge['target']!r} "
                        f"!= resolved need {need_id!r}"
                    )
                if edge["semantic_strength"] != "derivation":
                    failures.append(
                        f"positive case {name}: unexpected strength "
                        f"{edge['semantic_strength']!r}"
                    )
                witness = edge.get("witness") or {}
                relationship_id = str(witness.get("relationship_id", ""))
                marker_usage_ids = [
                    str(item) for item in witness.get("marker_usage_ids") or []
                ]
                owner_ids = [
                    str(item) for item in witness.get("annotation_owner_ids") or []
                ]
                if not (
                    relationship_id
                    and marker_usage_ids
                    and all(marker_usage_ids)
                    and owner_ids
                    and all(owner_ids)
                ):
                    failures.append(
                        f"positive case {name}: incomplete discriminator "
                        f"witness {witness!r}"
                    )
                elif edge["api_object_id"] != relationship_id:
                    failures.append(
                        f"positive case {name}: witness relationship "
                        f"{relationship_id!r} does not match the edge "
                        f"dependency {edge['api_object_id']!r}"
                    )
                # Inverse navigation over the same witness from the need.
                inverse = service.semantic_neighbors(
                    expectation["need"],
                    predicates=[INVERSE_PREDICATE],
                )
                case["inverse_edges"] = inverse["edges"]
                inverse_edges = [
                    e
                    for e in inverse["edges"]
                    if e["api_object_id"] == edge["api_object_id"]
                    and e["target"] == source_id
                ]
                if len(inverse_edges) != 1:
                    failures.append(
                        f"positive case {name}: inverse navigation "
                        f"{INVERSE_PREDICATE} did not return the same witness "
                        f"reversed (got {len(inverse_edges)} matching edges)"
                    )
                elif inverse["gaps"]:
                    failures.append(
                        f"positive case {name}: inverse navigation reported "
                        f"gaps {inverse['gaps']!r}"
                    )
        except Exception as exc:  # noqa: BLE001 - proof must observe failures
            failures.append(f"positive case {name} raised {type(exc).__name__}: {exc}")
            case["error"] = f"{type(exc).__name__}: {exc}"
        report["cases"].append(case)  # type: ignore[union-attr]

    # Adversarial cases: zero edges required; an exception is also a failure.
    for name in ADVERSARIAL_CASES:
        case = {"case": name, "kind": "adversarial"}
        try:
            result = service.semantic_neighbors(
                name, predicates=[FORWARD_PREDICATE]
            )
            edges = result["edges"]
            case["edges"] = edges
            case["gaps"] = result["gaps"]
            if edges:
                failures.append(
                    f"adversarial case {name} produced {len(edges)} derivation "
                    f"edge(s); unmarked dependencies must not satisfy the "
                    f"predicate"
                )
        except Exception as exc:  # noqa: BLE001
            failures.append(
                f"adversarial case {name} raised {type(exc).__name__}: {exc}"
            )
            case["error"] = f"{type(exc).__name__}: {exc}"
        report["cases"].append(case)  # type: ignore[union-attr]

    report["failures"] = failures  # type: ignore[assignment]
    report["verdict"] = "pass" if not failures else "fail"  # type: ignore[assignment]
    payload = json.dumps(report, indent=1, sort_keys=True)
    if args.output is not None:
        args.output.write_text(payload, encoding="utf-8")
    print(payload)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
