"""Prove the derivesRequirementFromNeed slice against one validated API revision.

Loads the revision binding (including ingestion-validated kernel bindings),
assembles the existing semantic runtime, and queries the predicate for real
AEBS requirements. Positive cases must return discriminated edges; the
adversarial case (a relevance dependency with Requirement->Requirement
endpoints but no marker) must return no edge for that predicate.

Usage:
    python scripts/prove_derivation_slice.py \
        --api-url https://sysml-api.de4sdv.org \
        --binding <binding.json> \
        [--output /tmp/derivation-proof.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from de4sdv.semantic.runtime import build_semantic_runtime

ROOT = Path(__file__).resolve().parents[1]

POSITIVE_CASES = (
    "reqCommandEmergencyBraking",
    "reqDetectForwardCollisionRisk",
    "reqProvideCollisionWarning",
    "reqPedestrianTargetResponse",
    "reqBicycleTargetResponse",
)

ADVERSARIAL_CASES = (
    # Requirement->RequirementUsage relevance/trace dependencies without the
    # derivation marker (UG-05): the predicate must not fire on endpoint
    # types alone.
    "reqResistFalseReaction",        # its relevance deps are not derivations
    "reqAllowDriverOverride",        # has relevance deps to evidence contracts
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--binding", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    binding = json.loads(args.binding.read_text(encoding="utf-8"))
    service = build_semantic_runtime(
        api_url=args.api_url,
        binding_path=args.binding,
        expected_git_revision=binding["git_commit"],
        ontology_path=ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml",
    )

    report: dict[str, object] = {
        "schema": "de4sdv-derivation-slice-proof/v1",
        "revision": service._revision(),
        "cases": [],
    }
    failures: list[str] = []

    for name in POSITIVE_CASES:
        result = service.semantic_neighbors(name, predicates=["derivesRequirementFromNeed"])
        edges = result["edges"]
        gaps = result["gaps"]
        case = {
            "case": name,
            "kind": "positive",
            "edges": edges,
            "gaps": gaps,
        }
        report["cases"].append(case)  # type: ignore[union-attr]
        if not edges:
            failures.append(f"positive case {name} returned no derivation edge")
        for edge in edges:
            if edge["semantic_strength"] != "derivation":
                failures.append(f"{name}: unexpected strength {edge['semantic_strength']!r}")

    for name in ADVERSARIAL_CASES:
        result = service.semantic_neighbors(name, predicates=["derivesRequirementFromNeed"])
        edges = result["edges"]
        case = {
            "case": name,
            "kind": "adversarial",
            "edges": edges,
            "gaps": result["gaps"],
        }
        report["cases"].append(case)  # type: ignore[union-attr]
        if edges:
            failures.append(
                f"adversarial case {name} produced {len(edges)} derivation edge(s); "
                f"unmarked dependencies must not satisfy the predicate"
            )

    report["failures"] = failures  # type: ignore[assignment]
    report["verdict"] = "pass" if not failures else "fail"  # type: ignore[assignment]
    payload = json.dumps(report, indent=1, sort_keys=True)
    if args.output is not None:
        args.output.write_text(payload, encoding="utf-8")
    print(payload)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
