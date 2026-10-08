"""The DE4SDV kernel contract: class and relationship mappings of the method kernel.

O4 Wave C2: the contract is built from the model-generated projection layers
(:func:`KernelContract.from_layers`, :mod:`de4sdv.semantic.model_contract`).
The class name is kept (owner decision D7); its fields are the same shape the
runtime, traversal, query and impact consumers read.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from de4sdv.sysml_api.revisions import OntologyIdentity


ROOT = Path(__file__).resolve().parents[2]

_DECLARATION = re.compile(r"^(.+?)\s+def\s+([A-Za-z][A-Za-z0-9_]*)$")


def declaration_identity(declaration: str) -> tuple[str, str]:
    """Declared name and API element type for one kernel declaration string."""
    match = _DECLARATION.fullmatch(" ".join(declaration.split()))
    if not match:
        raise ValueError(f"unsupported kernel declaration syntax: {declaration!r}")
    kind, name = match.groups()
    kind_words = kind.split()
    if kind_words and kind_words[0] == "variation":
        kind_words = kind_words[1:]
    special = {"enum": "Enumeration", "use case": "UseCase"}
    normalized_kind = " ".join(kind_words)
    type_stem = special.get(
        normalized_kind,
        "".join(word[:1].upper() + word[1:] for word in kind_words),
    )
    return name, f"{type_stem}Definition"


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


class RetiredIdentityError(KeyError):
    """A retired or refused identity was requested (O4 Wave C2, D4/D5).

    A ``KeyError`` subclass so callers that treat an unknown identity as
    absent keep working; the message carries the disposition (``retired;
    use <successor>`` or the register disposition), never an answer.
    """

    def __init__(self, identity: str, disposition: str) -> None:
        super().__init__(f"{identity}: {disposition}")
        self.identity = identity
        self.disposition = disposition

    def __str__(self) -> str:
        return f"{self.identity}: {self.disposition}"


@dataclass(frozen=True)
class RelationshipMapping:
    name: str
    strategy: str
    semantic_strength: str
    configuration: dict[str, Any]
    #: Governed semantic domain/range ontology class names — the predicate's
    #: declared semantic contract. Representation mechanics are held to this
    #: contract (c3: the subject-membership strategy enforces both lineages
    #: through the validated kernel bindings); mechanics never author a
    #: second, competing type contract.
    domain: str | None = None
    range: str | None = None


@dataclass(frozen=True)
class KernelContract:
    source: Path
    identity: OntologyIdentity
    governed_directory: str
    exclusions: dict[str, dict[str, str]]
    classes: dict[str, dict[str, Any]]
    relationships: dict[str, dict[str, Any]]
    #: Model-built contracts carry their resolved mappings directly; the
    #: ``classes``/``relationships`` dictionaries are the same content in the
    #: shape the consumers iterate. ``refused`` maps retired/refused identity
    #: names to their disposition.
    class_mappings: Mapping[str, Any] | None = None
    relationship_mappings: Mapping[str, Any] | None = None
    refused: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def from_layers(cls, root: Path = ROOT) -> "KernelContract":
        """The contract built from the model-generated projection layers."""
        from .model_contract import build_model_contract

        return build_model_contract(Path(root))

    def _refuse(self, name: str) -> None:
        disposition = (self.refused or {}).get(name)
        if disposition is not None:
            raise RetiredIdentityError(name, disposition)

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
        return cls(
            path,
            OntologyIdentity.from_file(path, repository_root=ROOT),
            governed,
            exclusions,
            classes,
            relationships,
        )

    def mapping(self, ontology_class: str) -> KernelMapping:
        if self.class_mappings is not None:
            self._refuse(ontology_class)
            if ontology_class not in self.class_mappings:
                raise KeyError(f"ontology class has no kernel mapping: {ontology_class}")
            return self.class_mappings[ontology_class]
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
        if self.relationship_mappings is not None:
            self._refuse(relationship)
            mapping = self.relationship_mappings.get(relationship)
            if mapping is None:
                raise KeyError(f"ontology relationship has no SysML mapping: {relationship}")
            return mapping
        try:
            spec = self.relationships[relationship]
            value = spec["sysml_mapping"]
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
        domain = spec.get("domain")
        range_ = spec.get("range")
        return RelationshipMapping(
            name=relationship,
            strategy=value["strategy"],
            semantic_strength=strength,
            configuration={
                key: item
                for key, item in value.items()
                if key not in {"strategy", "semantic_strength", "domain", "range"}
            },
            domain=domain if isinstance(domain, str) else None,
            range=range_ if isinstance(range_, str) else None,
        )
