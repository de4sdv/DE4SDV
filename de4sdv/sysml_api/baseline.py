"""Reviewed SysML baseline source manifest for API ingestion."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REVIEWED_ROOTS = (
    Path("textual-notation-of-model"),
    Path("model-based-product-line-engineering/product-models"),
)
PINNED_DEPENDENCIES = (
    Path(".sysand/lib/mbse4u-sysmod_5.1.1/SYSMOD.sysml"),
    Path(
        ".sysand/lib/ode4hera-requirements-management_2.0.1/"
        "RequirementsManagement.sysml"
    ),
    Path(".sysand/lib/sensmetry-syside-views_0.10.3/SysideViews.sysml"),
)


@dataclass(frozen=True)
class BaselineSource:
    path: str
    authority: str
    sha256: str
    size: int


@dataclass(frozen=True)
class BaselineManifest:
    sources: tuple[BaselineSource, ...]

    @classmethod
    def discover(cls, repository_root: Path) -> "BaselineManifest":
        entries: list[BaselineSource] = []
        for root in REVIEWED_ROOTS:
            for path in sorted((repository_root / root).rglob("*.sysml")):
                relative = path.relative_to(repository_root)
                if "snapshots" in relative.parts:
                    continue
                entries.append(_source(repository_root, relative, "reviewed"))
        for relative in PINNED_DEPENDENCIES:
            entries.append(_source(repository_root, relative, "pinned-dependency"))
        return cls(tuple(entries))


@dataclass(frozen=True)
class BaselineExportBundle:
    git_commit: str
    elements: dict[str, dict[str, Any]]
    element_sources: dict[str, str]
    external_references: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "de4sdv-sysml-api-baseline-export/v1",
            "git_commit": self.git_commit,
            "elements": [self.elements[element_id] for element_id in sorted(self.elements)],
            "element_sources": self.element_sources,
            "external_references": list(self.external_references),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "BaselineExportBundle":
        if value.get("schema") != "de4sdv-sysml-api-baseline-export/v1":
            raise ValueError("unsupported baseline export schema")
        raw_elements = value.get("elements")
        if not isinstance(raw_elements, list) or not all(
            isinstance(element, dict) for element in raw_elements
        ):
            raise ValueError("baseline export elements must be a list of objects")
        elements = {
            str(element["@id"]): element
            for element in raw_elements
            if isinstance(element.get("@id"), str)
        }
        if len(elements) != len(raw_elements):
            raise ValueError("baseline export contains missing or duplicate element IDs")
        sources = value.get("element_sources")
        external = value.get("external_references")
        if not isinstance(sources, dict) or not all(
            isinstance(key, str) and isinstance(path, str)
            for key, path in sources.items()
        ):
            raise ValueError("baseline export element_sources must map IDs to paths")
        if set(sources) != set(elements):
            raise ValueError("baseline export element_sources do not cover every element")
        if not isinstance(external, list) or not all(
            isinstance(reference, dict) for reference in external
        ):
            raise ValueError("baseline export external_references must be a list")
        return cls(
            git_commit=str(value.get("git_commit", "")),
            elements=elements,
            element_sources=dict(sources),
            external_references=tuple(external),
        )

    @classmethod
    def load(cls, path: Path) -> "BaselineExportBundle":
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("baseline export must be a JSON object")
        return cls.from_dict(value)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def build_export_bundle(
    *,
    git_commit: str,
    source_documents: dict[str, list[dict[str, Any]]],
) -> BaselineExportBundle:
    """Combine official serializer output and separate out-of-bundle references.

    This adapts standard JSON objects to the API service payload shape. It does
    not parse or reconstruct textual SysML.
    """
    raw: dict[str, dict[str, Any]] = {}
    sources: dict[str, str] = {}
    for source_path, elements in source_documents.items():
        for element in elements:
            element_id = element.get("@id")
            element_type = element.get("@type")
            if not isinstance(element_id, str) or not element_id:
                raise ValueError(f"exported element in {source_path} has no @id")
            if not isinstance(element_type, str) or not element_type:
                raise ValueError(
                    f"exported element {element_id} in {source_path} has no @type"
                )
            previous = raw.get(element_id)
            if previous is not None and previous != element:
                raise ValueError(
                    f"conflicting exported element {element_id}: "
                    f"{sources[element_id]} and {source_path}"
                )
            raw[element_id] = copy.deepcopy(element)
            sources.setdefault(element_id, source_path)

    known_ids = set(raw)
    external: list[dict[str, str]] = []
    normalized = {
        element_id: _normalize_value(
            element,
            known_ids=known_ids,
            source_element_id=element_id,
            path="",
            external=external,
        )
        for element_id, element in raw.items()
    }
    return BaselineExportBundle(
        git_commit=git_commit,
        elements=normalized,
        element_sources=sources,
        external_references=tuple(external),
    )


_OMIT = object()


def _normalize_value(
    value: Any,
    *,
    known_ids: set[str],
    source_element_id: str,
    path: str,
    external: list[dict[str, str]],
) -> Any:
    if isinstance(value, dict):
        is_reference = "@id" in value and "@type" not in value
        if is_reference:
            target_id = value.get("@id")
            if isinstance(target_id, str) and target_id not in known_ids:
                external.append(
                    {
                        "source_element_id": source_element_id,
                        "property_path": path,
                        "target_id": target_id,
                        "uri": str(value.get("@uri", "")),
                    }
                )
                return _OMIT
            return {"@id": target_id}
        result: dict[str, Any] = {}
        for key, item in value.items():
            child_path = f"{path}.{key}" if path else key
            normalized = _normalize_value(
                item,
                known_ids=known_ids,
                source_element_id=source_element_id,
                path=child_path,
                external=external,
            )
            if normalized is not _OMIT and normalized != []:
                result[key] = normalized
        return result
    if isinstance(value, list):
        list_result: list[Any] = []
        for index, item in enumerate(value):
            normalized = _normalize_value(
                item,
                known_ids=known_ids,
                source_element_id=source_element_id,
                path=f"{path}[{index}]",
                external=external,
            )
            if normalized is not _OMIT:
                list_result.append(normalized)
        return list_result
    return value


def _source(repository_root: Path, relative: Path, authority: str) -> BaselineSource:
    path = repository_root / relative
    data = path.read_bytes()
    return BaselineSource(
        path=relative.as_posix(),
        authority=authority,
        sha256=hashlib.sha256(data).hexdigest(),
        size=len(data),
    )
