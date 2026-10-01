"""Explicit non-production composition; production legacy/O3 selectors stay frozen.

The frozen O3 provider owns its reviewed identities, the verified definition
pair owns only its disjoint admitted classes, and all others explicitly use
the authored KernelContract. There is no retry/fallback on a migrated error.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from .authority_selection import AuthoritySelectionError
from .o3_bundle import MIGRATED_CLASSES, MIGRATED_IDENTITIES, MIGRATED_RELATIONSHIPS, O3ImpactService
from .query import SemanticQueryService

COMPOSITION = "o3+definitions"


def _component_provenance(contract):
    return [
        {"authority": "semantic-authority", "source": f"projection://{contract._o3.authority_id}"},
        {"authority": "semantic-authority", "source": f"definition-projection://{contract._definitions.authority_id}"},
        {"authority": "runtime-implementation", "source": f"implementation://{contract._implementation_manifest['id']}"},
        {"authority": "unmigrated-semantic-fallback", "source": str(contract._legacy.source)},
    ]


class CompositeQueryService(SemanticQueryService):
    def _provenance(self):
        return super()._provenance() + _component_provenance(self.contract)


class CompositeImpactService(O3ImpactService):
    def impact(self, identifier, *, git_revision):
        report = super().impact(identifier, git_revision=git_revision)
        report["provenance"] += _component_provenance(self.contract)
        report["semantic_authority"] = self.contract.provenance()
        return report


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def composition_identity(*, bundle_id: str, candidate: Any,
                         binding_digest: str, implementation_manifest: Mapping) -> str:
    payload = dict(schema="de4sdv.o4-runtime-composition/v1", bundle_id=bundle_id,
                   candidate=_plain(dict(source_revision=candidate.source_revision,
                                        bound_inputs=candidate.bound_inputs,
                                        identities=candidate.identities,
                                        rows=candidate.rows, entries=candidate.entries)),
                   binding_digest=binding_digest, implementation_manifest=_plain(implementation_manifest))
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return "o4-composite:" + digest


class CompositeAuthority:
    """One disjoint routing table, including explicit remaining legacy authority."""

    def __init__(self, *, o3, definitions, legacy, authority_id, implementation_manifest):
        names = definitions.identities
        if (not names or len(names) != len(set(names))
                or any(not isinstance(n, str) or not n.strip() or n != n.strip() for n in names)):
            raise AuthoritySelectionError("malformed or duplicate definition admissions")
        overlap = set(names) & set(MIGRATED_IDENTITIES)
        if overlap:
            raise AuthoritySelectionError(f"overlapping admissions: {sorted(overlap)}")
        if not definitions.closure.closed:
            raise AuthoritySelectionError(definitions.closure.prerequisite())
        if o3.facade.identity != legacy.identity or definitions.provider.identity != legacy.identity:
            raise AuthoritySelectionError("component ontology identity conflict")
        self._o3 = o3
        self._definitions = definitions
        self._legacy = legacy
        self._implementation_manifest = MappingProxyType({
            "schema": implementation_manifest["schema"],
            "id": implementation_manifest["id"],
            "files": MappingProxyType(dict(implementation_manifest["files"])),
        })
        self._admitted = frozenset(names)
        self.identity = legacy.identity
        self.authority_id = authority_id
        self.migrated_identities = tuple(MIGRATED_IDENTITIES) + tuple(names)
        self.classes = dict(o3.facade.classes)
        for name in names:
            self.classes[name] = definitions.provider.classes[name]
        self.relationships = dict(o3.facade.relationships)

    def mapping(self, name):
        if name in MIGRATED_CLASSES:
            return self._o3.facade.mapping(name)
        if name in self._admitted:
            return self._definitions.provider.mapping(name)
        return self._legacy.mapping(name)

    def class_mapping(self, name):
        if name in MIGRATED_CLASSES:
            return self._o3.facade.class_mapping(name)
        if name in self._admitted:
            return self._definitions.provider.class_mapping(name)
        return self._legacy.class_mapping(name)

    def relationship_mapping(self, name):
        if name in MIGRATED_RELATIONSHIPS:
            return self._o3.facade.relationship_mapping(name)
        return self._legacy.relationship_mapping(name)

    def provenance(self):
        return dict(kind=COMPOSITION, authority_id=self.authority_id,
                    o3_authority_id=self._o3.authority_id,
                    definition_authority_id=self._definitions.authority_id,
                    implementation_manifest=_plain(self._implementation_manifest),
                    migrated_identities=list(self.migrated_identities),
                    fallback="explicit authored contract for unmigrated identities only",
                    activation_blocked=True, o3_activation_blocked=self._o3.activation_blocked,
                    status="non-production; whole-consumer retirement pending")
