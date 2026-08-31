"""Loader for the merged PR #168 ontology/kernel contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class KernelFileMapping:
    file: str
    declaration: str


@dataclass(frozen=True)
class KernelNativeMapping:
    native: str


@dataclass(frozen=True)
class KernelExternalMapping:
    external: str


KernelMapping = KernelFileMapping | KernelNativeMapping | KernelExternalMapping


@dataclass(frozen=True)
class RelationshipMapping:
    name: str
    strategy: str
    semantic_strength: str
    configuration: dict[str, Any]


@dataclass(frozen=True)
class KernelContract:
    source: Path
    governed_directory: str
    exclusions: dict[str, dict[str, str]]
    classes: dict[str, dict[str, Any]]
    relationships: dict[str, dict[str, Any]]

    @classmethod
    def load(cls, path: Path) -> "KernelContract":
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("ontology document must be a YAML mapping")
        sync = value.get("kernel_sync")
        classes = value.get("classes")
        relationships = value.get("relationships")
        if not isinstance(sync, dict):
            raise ValueError("ontology has no kernel_sync contract")
        governed = sync.get("governed_directory")
        exclusions = sync.get("exclusions")
        if not isinstance(governed, str) or not governed:
            raise ValueError("kernel_sync.governed_directory is missing")
        if not isinstance(exclusions, dict):
            raise ValueError("kernel_sync.exclusions must be a mapping")
        if not isinstance(classes, dict) or not classes:
            raise ValueError("ontology classes must be a non-empty mapping")
        if not isinstance(relationships, dict):
            raise ValueError("ontology relationships must be a mapping")
        return cls(path, governed, exclusions, classes, relationships)

    def mapping(self, ontology_class: str) -> KernelMapping:
        try:
            value = self.classes[ontology_class]["kernel"]
        except (KeyError, TypeError) as exc:
            raise KeyError(f"ontology class has no kernel mapping: {ontology_class}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"invalid kernel mapping for {ontology_class}")
        if isinstance(value.get("file"), str) and isinstance(value.get("declaration"), str):
            return KernelFileMapping(value["file"], value["declaration"])
        if isinstance(value.get("native"), str):
            return KernelNativeMapping(value["native"])
        if isinstance(value.get("external"), str):
            return KernelExternalMapping(value["external"])
        raise ValueError(f"unrecognized kernel mapping for {ontology_class}")

    def class_mapping(self, ontology_class: str) -> KernelFileMapping:
        mapping = self.mapping(ontology_class)
        if not isinstance(mapping, KernelFileMapping):
            raise ValueError(f"ontology class {ontology_class} is not file-mapped")
        return mapping

    def relationship_mapping(self, relationship: str) -> RelationshipMapping:
        try:
            value = self.relationships[relationship]["sysml_mapping"]
        except (KeyError, TypeError) as exc:
            raise KeyError(
                f"ontology relationship has no SysML mapping: {relationship}"
            ) from exc
        if not isinstance(value, dict) or not isinstance(value.get("strategy"), str):
            raise ValueError(f"invalid SysML mapping for relationship {relationship}")
        strength = value.get("semantic_strength", "native")
        if not isinstance(strength, str):
            raise ValueError(
                f"invalid semantic_strength for relationship {relationship}"
            )
        return RelationshipMapping(
            name=relationship,
            strategy=value["strategy"],
            semantic_strength=strength,
            configuration={
                key: item
                for key, item in value.items()
                if key not in {"strategy", "semantic_strength"}
            },
        )
