"""Complete ontology/kernel binding validation against one imported API revision."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from de4sdv.sysml_api.repository import element_id

from .kernel_contract import declaration_identity
from .kernel_contract import (
    KernelContract,
    KernelExternalMapping,
    KernelFileMapping,
    KernelNativeMapping,
)

BindingStatus = Literal["mapped", "native", "external", "lineage-pinned", "unresolved",
                        "ambiguous"]


@dataclass(frozen=True)
class OntologyBindingValidation:
    ontology_class: str
    status: BindingStatus
    mapping: dict[str, str]
    element_ids: tuple[str, ...] = ()
    api_type: str | None = None
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OntologyBindingReport:
    entries: tuple[OntologyBindingValidation, ...]
    summary: dict[str, int]

    @property
    def passed(self) -> bool:
        return self.summary["unresolved"] == 0 and self.summary["ambiguous"] == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "de4sdv-ontology-api-binding-report/v1",
            "passed": self.passed,
            "summary": self.summary,
            "bindings": [entry.to_dict() for entry in self.entries],
        }


def validate_ontology_bindings(
    contract: KernelContract,
    elements: list[dict[str, Any]],
    element_sources: dict[str, str],
) -> OntologyBindingReport:
    """Classify every ontology class without silently choosing an API object."""
    entries: list[OntologyBindingValidation] = []
    lineage_pinned = getattr(contract, "lineage_pinned", None) or {}
    for ontology_class in contract.classes:
        mapping = contract.mapping(ontology_class)
        if ontology_class in lineage_pinned:
            owner = lineage_pinned[ontology_class]
            entries.append(
                OntologyBindingValidation(
                    ontology_class=ontology_class,
                    status="lineage-pinned",
                    mapping={"file": mapping.file, "declaration": mapping.declaration},
                    detail=(f"lineage pin of {owner}: the pin is bound under {owner} "
                            "and the successor routing resolves this class from it"),
                )
            )
            continue
        if isinstance(mapping, KernelNativeMapping):
            entries.append(
                OntologyBindingValidation(
                    ontology_class=ontology_class,
                    status="native",
                    mapping={"native": mapping.native},
                    detail="native SysML category; no single kernel declaration is required",
                )
            )
            continue
        if isinstance(mapping, KernelExternalMapping):
            entries.append(
                OntologyBindingValidation(
                    ontology_class=ontology_class,
                    status="external",
                    mapping={"external": mapping.external},
                    detail="authoritative object is outside the SysML API baseline",
                )
            )
            continue
        if not isinstance(mapping, KernelFileMapping):
            raise TypeError(f"unsupported kernel mapping: {mapping!r}")
        name, expected_type = declaration_identity(mapping.declaration)
        matching_identity = [
            candidate
            for candidate in elements
            if candidate.get("@type") == expected_type
            and (candidate.get("declaredName") or candidate.get("name")) == name
        ]
        candidates = [
            candidate
            for candidate in matching_identity
            if (candidate_id := element_id(candidate)) is not None
            and element_sources.get(candidate_id) == mapping.file
        ]
        ids = tuple(
            sorted(
                candidate_id
                for candidate in candidates
                if (candidate_id := element_id(candidate)) is not None
            )
        )
        common = {
            "ontology_class": ontology_class,
            "mapping": {"file": mapping.file, "declaration": mapping.declaration},
            "element_ids": ids,
            "api_type": expected_type,
        }
        if len(candidates) == 1:
            entries.append(OntologyBindingValidation(status="mapped", **common))
        elif len(candidates) > 1:
            entries.append(
                OntologyBindingValidation(
                    status="ambiguous",
                    detail=f"exact file/declaration mapping resolved to {len(candidates)} UUIDs",
                    **common,
                )
            )
        else:
            wrong_source_count = len(matching_identity)
            detail = "exact file/declaration mapping did not resolve"
            if wrong_source_count:
                detail += f"; {wrong_source_count} name/type matches had different provenance"
            entries.append(
                OntologyBindingValidation(status="unresolved", detail=detail, **common)
            )
    summary = {
        status: sum(entry.status == status for entry in entries)
        for status in ("mapped", "native", "external", "lineage-pinned", "unresolved",
                       "ambiguous")
    }
    return OntologyBindingReport(tuple(entries), summary)


#: Tracked model-provider artifacts whose rows may state a projected kernel
#: binding contract (``grounding.kernel_binding_contract``). Batch files added
#: under the same directories are picked up by the same pattern.
MODEL_PROVIDER_PATTERN = "docs/method-conformance/**/*projection*.json"
MODEL_PROVIDER_CROSS_CHECK_SCHEMA = "de4sdv.o4-model-provider-cross-check/v1"


def _projected_kernel_bindings(document: object, identity: str | None = None):
    if isinstance(document, dict):
        identity = document.get("identity", identity)
        for key, value in document.items():
            if key == "kernel_binding_contract" and isinstance(value, dict):
                yield identity, value
            else:
                yield from _projected_kernel_bindings(value, identity)
    elif isinstance(document, list):
        for item in document:
            yield from _projected_kernel_bindings(item, identity)


def cross_check_model_provider(
    contract: object, kernel_bindings: list[dict], *, root: Path
) -> dict[str, object]:
    """Cross-check: model-built contract mapping vs every tracked projection.

    Every identity a tracked projection (live layers and frozen O2 records)
    grounds through a kernel binding contract must carry the SAME (source
    file, declaration) in the model-built kernel contract. A mismatch, a
    projected identity the contract does not file-map, or two providers
    disagreeing on one identity is a refusal. The result lands in the
    semantic validation report.
    """
    providers: dict[str, dict[str, str]] = {}
    duplicates: list[dict[str, object]] = []
    sources: list[str] = []
    for path in sorted(root.glob(MODEL_PROVIDER_PATTERN)):
        relative = path.relative_to(root).as_posix()
        document = json.loads(path.read_text(encoding="utf-8"))
        found = False
        for identity, grounding in _projected_kernel_bindings(document):
            if not identity:
                continue
            found = True
            entry = {
                "source_file": str(grounding.get("source_file") or ""),
                "declaration": str(grounding.get("declaration") or ""),
                "provider": relative,
            }
            previous = providers.get(identity)
            if previous is None:
                providers[identity] = entry
            elif (previous["source_file"], previous["declaration"]) != (
                entry["source_file"], entry["declaration"]
            ):
                duplicates.append({"identity": identity, "providers": [previous, entry]})
        if found:
            sources.append(relative)
    ingested = {
        str(item.get("ontology_class")): str(item.get("element_id"))
        for item in kernel_bindings
    }
    rows: list[dict[str, object]] = []
    mismatches: list[dict[str, object]] = []
    for identity in sorted(providers):
        entry = providers[identity]
        try:
            mapping = contract.mapping(identity)  # type: ignore[attr-defined]
        except KeyError:
            mismatches.append({"identity": identity, **entry,
                               "reason": "projected identity has no kernel mapping in the model-built contract"})
            continue
        if not isinstance(mapping, KernelFileMapping):
            mismatches.append({"identity": identity, **entry,
                               "reason": "projected identity is not file-mapped in the model-built contract"})
            continue
        if (mapping.file, mapping.declaration) != (entry["source_file"], entry["declaration"]):
            mismatches.append({"identity": identity, **entry,
                               "contract_source_file": mapping.file,
                               "contract_declaration": mapping.declaration,
                               "reason": "model-built contract and projected kernel binding contracts differ"})
            continue
        rows.append({"identity": identity, **entry,
                     "ingested_element_id": ingested.get(identity)})
    if mismatches or duplicates:
        classification = "BLOCKING_MISMATCH"
    elif not providers:
        classification = "NOT_YET_COMPARABLE"
    else:
        classification = "EQUIVALENT"
    return {
        "schema": MODEL_PROVIDER_CROSS_CHECK_SCHEMA,
        "classification": classification,
        "provider_sources": sources,
        "projected_identity_count": len(providers),
        "matched": len(rows),
        "rows": rows,
        "mismatches": mismatches,
        "duplicate_providers": duplicates,
    }
