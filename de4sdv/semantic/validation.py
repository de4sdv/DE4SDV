"""Complete ontology/kernel binding validation against one imported API revision."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from de4sdv.sysml_api.repository import element_id

from .api_binding import declaration_identity
from .kernel_contract import (
    KernelContract,
    KernelExternalMapping,
    KernelFileMapping,
    KernelNativeMapping,
)

BindingStatus = Literal["mapped", "native", "external", "unresolved", "ambiguous"]


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
    for ontology_class in contract.classes:
        mapping = contract.mapping(ontology_class)
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
        for status in ("mapped", "native", "external", "unresolved", "ambiguous")
    }
    return OntologyBindingReport(tuple(entries), summary)
