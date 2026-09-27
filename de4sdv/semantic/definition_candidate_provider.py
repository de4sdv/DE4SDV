"""O4 definition-candidate provider — explicit, non-default class resolution.

Serves the admitted definition identities' kernel class mappings from the
verified candidate pair (``definition-projection.json`` /
``definition-profile.json``, read through :mod:`definition_candidate`) while
every other identity delegates to the legacy kernel contract. The surface
mirrors the frozen O3 authority façade (``classes`` / ``relationships`` /
``mapping`` / ``class_mapping`` / ``relationship_mapping`` / ``identity``) so
a runtime assembly seam can consume it through the same interface.

Explicit construction only: no production caller selects this provider, the
runtime assembly seam is unchanged, and the frozen O3 path is untouched. It
creates no traversal, no API identity claim and no authority activation — the
admitted rows stay vocabulary-only until their forward evidence exists.

Fail-closed: the provider is built from an already-validated candidate; a row
without a complete file/declaration contract is refused instead of producing a
silent partial provider.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .definition_candidate import DefinitionCandidate
from .kernel_contract import (
    KernelContract,
    KernelFileMapping,
    RelationshipMapping,
)


class DefinitionCandidateProvider:
    """Candidate class-resolution surface for the admitted definitions.

    Admitted identities resolve EXCLUSIVELY from the candidate pair; every
    other identity delegates explicitly to the legacy contract. There is no
    fallback between the two providers and never two providers for one
    identity.
    """

    def __init__(
        self, *, legacy: KernelContract, candidate: DefinitionCandidate
    ) -> None:
        self._legacy = legacy
        self._candidate = candidate
        mappings: dict[str, KernelFileMapping] = {}
        for name in candidate.identities:
            row = candidate.row_for(name)
            grounding = row.get("grounding")
            contract = (
                grounding.get("kernel_binding_contract")
                if isinstance(grounding, Mapping)
                else None
            )
            if not isinstance(contract, Mapping):
                raise ValueError(
                    f"admitted identity {name!r} lacks a kernel binding contract"
                )
            source_file = contract.get("source_file")
            declaration = contract.get("declaration")
            if (
                not isinstance(source_file, str)
                or not source_file.strip()
                or not isinstance(declaration, str)
                or not declaration.strip()
            ):
                raise ValueError(
                    f"admitted identity {name!r} lacks a complete "
                    "file/declaration contract"
                )
            mappings[name] = KernelFileMapping(source_file, declaration)
        self._admitted_mappings = mappings
        self.authority_id = f"definition-candidate:{candidate.source_revision}"
        self.identity = legacy.identity
        self.classes = self._merged_classes()
        self.relationships = dict(legacy.relationships)

    def _merged_classes(self) -> dict[str, Any]:
        merged = dict(self._legacy.classes)
        for name, mapping in self._admitted_mappings.items():
            merged[name] = {
                "kernel": {
                    "file": mapping.file,
                    "declaration": mapping.declaration,
                }
            }
        return merged

    def mapping(self, ontology_class: str) -> Any:
        if ontology_class in self._admitted_mappings:
            return self._admitted_mappings[ontology_class]
        return self._legacy.mapping(ontology_class)

    def class_mapping(self, ontology_class: str) -> KernelFileMapping:
        if ontology_class in self._admitted_mappings:
            return self._admitted_mappings[ontology_class]
        return self._legacy.class_mapping(ontology_class)

    def relationship_mapping(self, relationship: str) -> RelationshipMapping:
        return self._legacy.relationship_mapping(relationship)
