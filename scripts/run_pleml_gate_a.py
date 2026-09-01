#!/usr/bin/env python3
"""Import, query, evaluate, and report the revision-bound Gate A spike."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.sysml_api.baseline import BaselineExportBundle
from de4sdv.sysml_api.client import ApiClient
from de4sdv.sysml_api.ingestion import import_baseline
from de4sdv.sysml_api.repository import SysMLRepository, element_id
from de4sdv.sysml_api.revisions import RevisionBinding
from tools.pleml_gate_a import (
    GateAModel,
    DerivationOutcome,
    UnsupportedSemanticShape,
    build_observability_matrix,
    gate_a_source_identity,
)


def _reference_paths(value: object, path: str = "") -> list[dict[str, str]]:
    references: list[dict[str, str]] = []
    if isinstance(value, dict):
        if "@id" in value and "@type" not in value:
            target = value.get("@id")
            if isinstance(target, str):
                references.append({"property_path": path, "target_uuid": target})
            return references
        for key, item in value.items():
            child_path = f"{path}.{key}" if path else key
            references.extend(_reference_paths(item, child_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            references.extend(_reference_paths(item, f"{path}[{index}]"))
    return references


def _unique_named_id(
    elements: list[dict[str, Any]], name: str, metatypes: set[str]
) -> str:
    matches = [
        element_id(item)
        for item in elements
        if item.get("@type") in metatypes
        and (item.get("declaredName") or item.get("name")) == name
    ]
    matches = [item for item in matches if item]
    if len(matches) != 1:
        raise UnsupportedSemanticShape(
            f"expected one {sorted(metatypes)} named {name}, found {len(matches)}"
        )
    return matches[0]


def _qualified_name(elements: list[dict[str, Any]], target_id: str) -> str:
    by_id = {element_id(item): item for item in elements}
    names: list[str] = []
    current_id: str | None = target_id
    visited: set[str] = set()
    while current_id is not None and current_id not in visited:
        visited.add(current_id)
        current = by_id.get(current_id)
        if current is None:
            raise UnsupportedSemanticShape(
                f"qualified-name traversal lost API UUID {current_id}"
            )
        name = current.get("declaredName") or current.get("name")
        if isinstance(name, str) and name:
            names.append(name)
        owning = current.get("owningRelationship")
        owning_id = element_id(owning)
        if owning_id is None:
            break
        relationship = by_id.get(owning_id)
        if relationship is None:
            raise UnsupportedSemanticShape(
                f"qualified-name traversal lost ownership UUID {owning_id}"
            )
        current_id = element_id(relationship.get("owningRelatedElement"))
    qualified = "::".join(reversed(names))
    if not qualified:
        raise UnsupportedSemanticShape(f"API UUID {target_id} has no qualified name")
    return qualified


def _write_projection(
    path: Path,
    *,
    adapter_qualified_name: str,
    adapter_id: str,
    rule_id: str,
    configuration_id: str,
    sysml_commit_id: str,
    git_commit: str,
) -> None:
    content = f"""package GateAResolvedProjection {{
    private import GateAPLEMLFixture::*;

    doc /* Synthetic Gate A projection only.
         * Git commit: {git_commit}
         * SysML API commit: {sysml_commit_id}
         * configuration UUID: {configuration_id}
         * realization-rule UUID: {rule_id}
         * adapter-variant UUID: {adapter_id}
         */

    part gateADerivedAdapter :> {adapter_qualified_name};
}}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def serialize_outcomes(
    outcomes: dict[str, DerivationOutcome],
) -> dict[str, dict[str, Any]]:
    """JSON-safe outcome records; frozensets become sorted UUID lists."""

    serialized: dict[str, dict[str, Any]] = {}
    for name, outcome in outcomes.items():
        if not isinstance(outcome, DerivationOutcome):
            raise TypeError(f"expected DerivationOutcome for {name}")
        serialized[name] = {
            **asdict(outcome),
            "selected_feature_ids": sorted(outcome.selected_feature_ids),
        }
    return serialized


def run_gate_a(
    *,
    api_url: str,
    export_path: Path,
    report_path: Path,
    binding_path: Path,
    projection_path: Path,
) -> dict[str, Any]:
    raw = json.loads(export_path.read_text(encoding="utf-8"))
    exported_identity = raw.get("gate_a_identity")
    if not isinstance(exported_identity, dict):
        raise RuntimeError("Gate A export lacks exact source identity")
    current_identity = gate_a_source_identity(ROOT)
    expected_identity = {
        "scope": current_identity.scope,
        "git_repository": current_identity.git_repository,
        "git_commit": current_identity.git_commit,
        "pleml_commit": current_identity.pleml_commit,
        "serializer": "Syside official minimal JSON",
    }
    if exported_identity != expected_identity:
        raise RuntimeError(
            f"Gate A export identity mismatch: expected {expected_identity}, "
            f"got {exported_identity}"
        )
    bundle = BaselineExportBundle.from_dict(raw)
    if bundle.source_manifest != current_identity.source_manifest:
        raise RuntimeError("Gate A export source manifest is stale or incomplete")

    client = ApiClient(api_url)
    imported = import_baseline(client, bundle, project_name="DE4SDV PLEML Gate A")
    imported_at = datetime.now(timezone.utc).isoformat()
    binding = RevisionBinding(
        git_repository=current_identity.git_repository,
        git_commit=bundle.git_commit,
        sysml_project_id=imported.project_id,
        sysml_commit_id=imported.commit_id,
        import_timestamp=imported_at,
        import_tool_version="de4sdv-pleml-gate-a/v1",
        semantic_validation="passed",
        scope="fixture",
    )
    binding.require_current(current_identity.git_commit)
    binding_path.parent.mkdir(parents=True, exist_ok=True)
    binding_path.write_text(
        json.dumps(binding.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    repository = SysMLRepository(client)
    capabilities = repository.check_capabilities(
        binding.sysml_project_id, binding.sysml_commit_id
    )
    elements = repository.list_elements(
        binding.sysml_project_id, binding.sysml_commit_id
    )
    matrix = build_observability_matrix(elements, bundle.element_sources)
    model = GateAModel(elements)

    configs = {
        name: _unique_named_id(elements, name, {"OccurrenceUsage"})
        for name in (
            "validAutowareAndroid",
            "validAutowareNoMiddleware",
            "forbiddenApolloAndroid",
            "missingOpenpilotSCORE",
            "validBothSensors",
            "validOneSensor",
            "invalidNoSensor",
        )
    }
    nominal_rules = _unique_named_id(
        elements, "nominalAdapterRules", {"OccurrenceUsage"}
    )
    ambiguous_rules = _unique_named_id(
        elements, "ambiguousAdapterRules", {"OccurrenceUsage"}
    )
    outcomes = {
        "adapter-required-exactly-one": model.evaluate(
            configs["validAutowareAndroid"], rule_set_id=nominal_rules
        ),
        "valid-no-adapter": model.evaluate(
            configs["validAutowareNoMiddleware"], rule_set_id=nominal_rules
        ),
        "configuration-invalid": model.evaluate(
            configs["forbiddenApolloAndroid"], rule_set_id=nominal_rules
        ),
        "derivation-incomplete": model.evaluate(
            configs["missingOpenpilotSCORE"], rule_set_id=nominal_rules
        ),
        "derivation-ambiguous": model.evaluate(
            configs["validAutowareAndroid"], rule_set_id=ambiguous_rules
        ),
    }
    group_resolutions = {
        "at-least-one": model.group_resolutions(configs["validOneSensor"]),
        "multi-select": model.group_resolutions(configs["validBothSensors"]),
    }
    try:
        model.group_resolutions(configs["invalidNoSensor"])
    except UnsupportedSemanticShape as exc:
        group_empty_result: dict[str, Any] = {
            "status": "configuration-invalid",
            "derivation_attempted": False,
            "reason": str(exc),
        }
    else:
        raise RuntimeError(
            "empty at-least-one group resolution unexpectedly passed"
        )
    expected_statuses = {
        "adapter-required-exactly-one": "derivation-complete",
        "valid-no-adapter": "derivation-complete",
        "configuration-invalid": "configuration-invalid",
        "derivation-incomplete": "derivation-incomplete",
        "derivation-ambiguous": "derivation-ambiguous",
    }
    actual_statuses = {name: outcome.status for name, outcome in outcomes.items()}
    if actual_statuses != expected_statuses:
        raise RuntimeError(
            f"Gate A semantic outcomes differ: expected={expected_statuses}, "
            f"actual={actual_statuses}"
        )
    if outcomes["valid-no-adapter"].adapter_id is not None:
        raise RuntimeError("explicit no-adapter rule unexpectedly selected an adapter")
    resolved = outcomes["adapter-required-exactly-one"]
    if resolved.adapter_id is None or len(resolved.rule_ids) != 1:
        raise RuntimeError("exactly-one adapter outcome lacks UUID trace")
    adapter_name = _qualified_name(elements, resolved.adapter_id)
    _write_projection(
        projection_path,
        adapter_qualified_name=adapter_name,
        adapter_id=resolved.adapter_id,
        rule_id=resolved.rule_ids[0],
        configuration_id=resolved.configuration_id,
        sysml_commit_id=binding.sysml_commit_id,
        git_commit=binding.git_commit,
    )

    elements_by_id = {
        candidate_id: item
        for item in elements
        if (candidate_id := element_id(item)) is not None
    }
    trace_ids = set(configs.values()) | {nominal_rules, ambiguous_rules}
    for outcome in outcomes.values():
        trace_ids.update(outcome.selected_feature_ids)
        trace_ids.update(outcome.constraint_ids)
        trace_ids.update(outcome.rule_ids)
        if outcome.adapter_id is not None:
            trace_ids.add(outcome.adapter_id)
    api_shapes_by_uuid = {}
    for trace_id in sorted(trace_ids):
        item = elements_by_id.get(trace_id)
        if item is None:
            raise RuntimeError(f"outcome provenance lost API UUID {trace_id}")
        api_shapes_by_uuid[trace_id] = {
            "metatype": item.get("@type"),
            "name": item.get("declaredName") or item.get("name"),
            "source": bundle.element_sources.get(trace_id),
            "property_keys": sorted(item),
            "reference_paths": _reference_paths(item),
        }

    report: dict[str, Any] = {
        "schema": "de4sdv-pleml-gate-a-evidence/v1",
        "source_identity": expected_identity,
        "source_manifest": list(current_identity.source_manifest),
        "revision_binding": binding.to_dict(),
        "api_import": asdict(imported),
        "api_capabilities": capabilities,
        "observability_matrix": list(matrix),
        "outcomes": serialize_outcomes(outcomes),
        "group_resolutions": group_resolutions,
        "group_empty_result": group_empty_result,
        "validity_claim": (
            "Gate A proves the validity-versus-derivation phase boundary using "
            "modeled incompatibility semantics. Complete feature-configuration "
            "validity evaluation (cardinality, requiresFeatures propagation, "
            "lifecycle completeness) remains production evaluator work."
        ),
        "common_classification_claim": (
            "Evidence concept: common capability outside feature tree. Real "
            "common/variable portfolio classification and its SysML "
            "representation are established in Gate C from the real scope "
            "baseline; commonality is not inferred from the object name or "
            "from absence of a feature binding."
        ),
        "api_shapes_by_uuid": api_shapes_by_uuid,
        "projection": {
            "path": str(projection_path),
            "adapter_qualified_name": adapter_name,
            "configuration_uuid": resolved.configuration_id,
            "rule_uuid": resolved.rule_ids[0],
            "adapter_uuid": resolved.adapter_id,
        },
        "representation_attempts": [
            {
                "order": 1,
                "representation": "pinned PLEML FeatureBinding",
                "selected": False,
                "reason": (
                    "FeatureBinding exposes one dependency source/target mapping but "
                    "does not encode the required application AND middleware condition; "
                    "multiple bindings are not interpreted as conjunction."
                ),
            },
            {
                "order": 2,
                "representation": "native SysML constraint expression",
                "selected": False,
                "reason": (
                    "The expression probe is retained for exact serializer/API-shape "
                    "evidence, but a reusable realization table would require binding "
                    "configuration state into each constraint and an expression "
                    "interpreter outside the existing semantic repository."
                ),
            },
            {
                "order": 3,
                "representation": "narrow DE4SDV AdapterRealizationRule occurrence",
                "selected": True,
                "reason": (
                    "Three governed typed-reference roles survive as UUID-backed "
                    "FeatureValue/FeatureReferenceExpression paths. Both condition "
                    "roles are required and matched conjunctively; resultingAdapter is "
                    "optional only to model an explicit no-adapter result."
                ),
            },
        ],
        "source_fallback": {
            "necessary": False,
            "reason": "All evaluated engineering references were consumed from API objects.",
        },
        "external_manifest": {
            "necessary": False,
            "reason": "The narrow SysML extension represents and exposes the realization rule.",
        },
        "serializer_api_losses": [],
        "semantic_execution_gaps": [
            {
                "concept": "PLEML XORConstraint",
                "gap": (
                    "The official serializer preserves the constraint definition, "
                    "expression tree, redefinition, owner, and excluded-feature UUID, "
                    "but the API service and current DE4SDV repository do not execute "
                    "the expression. The spike evaluator therefore executes the "
                    "modeled xorFeatures relation by identity. The pinned expression's "
                    "range/index behavior remains a suspected upstream question."
                ),
            },
            {
                "concept": "native constraint expression",
                "gap": (
                    "The implies/and expression tree is observable, but no general "
                    "SysML expression interpreter exists in the DE4SDV semantic path."
                ),
            },
            {
                "concept": "inherited lifecycle defaults",
                "gap": (
                    "Explicit bindingTime overrides and the PLEML default are "
                    "observable by UUID, but inherited/default resolution requires "
                    "semantic traversal rather than a direct property on each feature."
                ),
            },
            {
                "concept": "requiresFeatures evaluation",
                "gap": (
                    "The requiresFeatures constraint shape is proven observable "
                    "by UUID (AssertConstraintUsage redefinition of the PLEML "
                    "base usage), but the spike evaluator does not execute "
                    "requires propagation; complete validity evaluation remains "
                    "production evaluator work."
                ),
            },
            {
                "concept": "group cardinality validation",
                "gap": (
                    "The spike evaluator resolves at-least-one/multi-select "
                    "group membership and fails closed on the empty-group case "
                    "by identity, but complete lower/upper cardinality "
                    "validation across arbitrary group shapes remains "
                    "production evaluator work."
                ),
            },
        ],
        "gate_a_disposition": "CONDITIONAL PASS",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--projection", type=Path, required=True)
    args = parser.parse_args()
    report = run_gate_a(
        api_url=args.api_url,
        export_path=args.export,
        report_path=args.report,
        binding_path=args.binding,
        projection_path=args.projection,
    )
    print(
        json.dumps(
            {
                "source_identity": report["source_identity"],
                "revision_binding": report["revision_binding"],
                "outcomes": {
                    name: value["status"] for name, value in report["outcomes"].items()
                },
                "report": str(args.report),
                "projection": str(args.projection),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
