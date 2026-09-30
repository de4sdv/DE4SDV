"""Bounded PLE qualification observations; never adoption or authority activation.

The frozen experiment is an input oracle, not a current toolchain. Fresh
serialization and API readback are performed by the runner, while this module
compares concept-specific observations without silently inferring semantics.
"""
from __future__ import annotations

from typing import Any


CASE_CONCEPTS = {
    "xor-counterexample": ("Incompatibility constraint", "Native constraint expression probe"),
    "feature-binding": ("FeatureBinding",),
    "group-shapes": ("At-least-one/multi-select group", "Group member (radar)",
                     "Group member (camera)", "Group multi-select resolution",
                     "Group at-least-one resolution"),
    "binding-time": ("Lifecycle metadata",),
    "serializer-identity": (),
    "adapter-realization": ("Adapter realization rule",),
}


def _index(matrix: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(matrix, (list, tuple)):
        raise ValueError("observability matrix must be an array")
    indexed = {}
    for row in matrix:
        if not isinstance(row, dict) or not isinstance(row.get("concept"), str) or not row["concept"]:
            raise ValueError("observability row requires a concept")
        if row["concept"] in indexed:
            raise ValueError("duplicate observability concept")
        for key in ("object_observable", "semantic_properties_retained", "provenance_retained", "api_only_consumption_adequate"):
            if type(row.get(key)) is not bool:
                raise ValueError("observability row requires explicit boolean adequacy fields")
        if not isinstance(row.get("exact_gap"), str) or not isinstance(row.get("evidence"), list):
            raise ValueError("observability row requires gap and evidence")
        if not all(isinstance(item, dict) and isinstance(item.get("metatype"), str) for item in row["evidence"]):
            raise ValueError("observability evidence requires metatypes")
        indexed[row["concept"]] = row
    return indexed


def _semantic_summary(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        **{key: row[key] for key in ("object_observable", "semantic_properties_retained", "provenance_retained", "api_only_consumption_adequate", "exact_gap")},
        "metatypes": sorted({item["metatype"] for item in row["evidence"]}),
    }


def build_case_report(matrix: Any, historical_matrix: Any) -> dict[str, Any]:
    current, historical = _index(matrix), _index(historical_matrix)
    differences = [
        {"concept": concept, "classification": "review-required",
         "before": _semantic_summary(historical.get(concept)),
         "after": _semantic_summary(current.get(concept))}
        for concept in sorted(set(current) | set(historical))
        if _semantic_summary(current.get(concept)) != _semantic_summary(historical.get(concept))
    ]
    cases = []
    for name, concepts in CASE_CONCEPTS.items():
        required = list(concepts) if concepts else sorted(current)
        missing = sorted(set(required) - set(current))
        observed = [current[concept] for concept in required if concept in current]
        inadequate = [row["concept"] for row in observed if not row["api_only_consumption_adequate"]]
        case = {"case": name, "status": "observed" if observed and not missing and not inadequate else "gap",
                "missing_concepts": missing, "inadequate_concepts": inadequate,
                "representation": observed, "qualified": False}
        if name == "xor-counterexample":
            case.update(native_expression_executed=False,
                        remaining_requirement="Execute the native XOR/range counterexample; a specialized incompatibility resolver is not native expression execution.")
        elif name == "feature-binding":
            case.update(multiple_binding_semantics_proven=False,
                        remaining_requirement="Exercise multiple bindings; do not infer AND/OR/precedence from single-linkage metadata.")
        elif name == "group-shapes":
            case["remaining_requirement"] = "Compare literal-bound and range-operator serialization; subsetting is not disjointness."
        elif name == "binding-time":
            case.update(stage_aware_evaluation_proven=False,
                        remaining_requirement="Development-stage metadata only; no lifecycle completeness or stage-aware evaluator claim.")
        elif name == "serializer-identity":
            case["remaining_requirement"] = "Runner must establish fresh UUID/metatype/internal-reference readback and retain pruning records; absent adequacy stays a gap."
        else:
            case["remaining_requirement"] = "Internal experimental pin-specific rule, not a product feature or adopted authority."
        cases.append(case)
    return {"schema": "de4sdv.ple-qualification-observations/v1", "cases": cases,
            "differences": differences, "qualified": False, "adoption_authorized": False,
            "authority_activation_authorized": False}
