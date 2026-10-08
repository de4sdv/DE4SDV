"""O4 definition-candidate provider — the verified definition pair's class mappings.

Serves the admitted definition identities' kernel class mappings from the
verified candidate pair (``definition-projection.json`` /
``definition-profile.json``, read through :mod:`definition_candidate`). The
model-authority runtime checks that its definition layer routes every
admitted identity to exactly these mappings. Any other identity is not
served here (``KeyError``); there is no fallback provider.

Fail-closed: a row without a complete file/declaration contract is refused
instead of producing a silent partial provider.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .definition_candidate import DefinitionCandidate
from .kernel_contract import KernelFileMapping


class DefinitionCandidateProvider:
    """Candidate class-resolution surface for the admitted definitions only."""

    def __init__(self, *, candidate: DefinitionCandidate) -> None:
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
        self.classes = {
            name: {"kernel": {"file": mapping.file, "declaration": mapping.declaration}}
            for name, mapping in mappings.items()
        }

    def mapping(self, ontology_class: str) -> Any:
        if ontology_class in self._admitted_mappings:
            return self._admitted_mappings[ontology_class]
        raise KeyError(f"not an admitted definition identity: {ontology_class}")

    def class_mapping(self, ontology_class: str) -> KernelFileMapping:
        return self.mapping(ontology_class)
