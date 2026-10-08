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

from de4sdv.sysml_api.revisions import SemanticAuthorityIdentity


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
    source: str
    identity: SemanticAuthorityIdentity
    governed_directory: str
    exclusions: dict[str, dict[str, str]]
    classes: dict[str, dict[str, Any]]
    relationships: dict[str, dict[str, Any]]
    #: The resolved mappings; ``classes``/``relationships`` are the same
    #: content in the shape the consumers iterate. ``refused`` maps
    #: retired/refused identity names to their disposition.
    class_mappings: Mapping[str, Any] | None = None
    relationship_mappings: Mapping[str, Any] | None = None
    refused: Mapping[str, str] = field(default_factory=dict)
    #: Natively represented classes whose file mapping is the lineage pin of
    #: their unique specializing class (name -> owning class). Ingestion binds
    #: the pin under its owner only; the successor routing resolves these.
    lineage_pinned: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def from_layers(cls, root: Path = ROOT) -> "KernelContract":
        """The contract built from the model-generated projection layers."""
        from .model_contract import build_model_contract

        return build_model_contract(Path(root))

    @classmethod
    def from_records(cls, *, classes: Mapping[str, Any], relationships: Mapping[str, Any],
                     identity: SemanticAuthorityIdentity, source: str = "records",
                     governed_directory: str = "", exclusions: Mapping[str, Any] | None = None,
                     refused: Mapping[str, str] | None = None) -> "KernelContract":
        """A contract from mapping records (``{"kernel": {...}}`` per class,
        ``{"sysml_mapping": {...}, "domain", "range", ...}`` per relationship).

        Used for synthetic contracts in tests and tooling; the runtime contract
        comes from :meth:`from_layers`.
        """
        class_mappings: dict[str, KernelMapping] = {}
        for name, record in classes.items():
            kernel = (record or {}).get("kernel") if isinstance(record, Mapping) else None
            if not isinstance(kernel, Mapping):
                raise ValueError(f"class record {name!r} has no kernel mapping")
            if isinstance(kernel.get("file"), str) and isinstance(kernel.get("declaration"), str):
                class_mappings[name] = KernelFileMapping(kernel["file"], kernel["declaration"])
            elif isinstance(kernel.get("native"), str):
                class_mappings[name] = KernelNativeMapping(kernel["native"])
            elif isinstance(kernel.get("external"), str):
                class_mappings[name] = KernelExternalMapping(kernel["external"])
            else:
                raise ValueError(f"unrecognized kernel mapping for {name}")
        relationship_mappings: dict[str, RelationshipMapping | None] = {}
        for name, spec in relationships.items():
            value = (spec or {}).get("sysml_mapping") if isinstance(spec, Mapping) else None
            if not isinstance(value, Mapping) or not isinstance(value.get("strategy"), str):
                relationship_mappings[name] = None
                continue
            strength = spec.get("semantic_strength", value.get("semantic_strength", "native"))
            relationship_mappings[name] = RelationshipMapping(
                name=name, strategy=value["strategy"], semantic_strength=str(strength),
                configuration={k: v for k, v in value.items()
                               if k not in {"strategy", "semantic_strength", "domain", "range"}},
                domain=spec.get("domain") if isinstance(spec.get("domain"), str) else None,
                range=spec.get("range") if isinstance(spec.get("range"), str) else None)
        return cls(source=source, identity=identity, governed_directory=governed_directory,
                   exclusions=dict(exclusions or {}),
                   classes={name: dict(record) for name, record in classes.items()},
                   relationships={name: dict(spec) for name, spec in relationships.items()},
                   class_mappings=class_mappings, relationship_mappings=relationship_mappings,
                   refused=dict(refused or {}))

    def _refuse(self, name: str) -> None:
        disposition = (self.refused or {}).get(name)
        if disposition is not None:
            raise RetiredIdentityError(name, disposition)

    def mapping(self, ontology_class: str) -> KernelMapping:
        self._refuse(ontology_class)
        if ontology_class not in (self.class_mappings or {}):
            raise KeyError(f"ontology class has no kernel mapping: {ontology_class}")
        return self.class_mappings[ontology_class]

    def class_mapping(self, ontology_class: str) -> KernelFileMapping:
        mapping = self.mapping(ontology_class)
        if not isinstance(mapping, KernelFileMapping):
            raise ValueError(f"ontology class {ontology_class} is not file-mapped")
        return mapping

    def relationship_mapping(self, relationship: str) -> RelationshipMapping:
        self._refuse(relationship)
        mapping = (self.relationship_mappings or {}).get(relationship)
        if mapping is None:
            raise KeyError(f"ontology relationship has no SysML mapping: {relationship}")
        return mapping
