"""Export documents: what the validated export records about its elements and the API does not carry.

The export records which source document produced each element, and the export adapter records each
reference whose target lies outside the export (ADR 0011). An API listing carries neither. The importer
records both in the revision binding (``export_documents``), from the export that the served-model
record names, after the full-payload read-back. An evaluation over the API then reads the export's own
documents from the binding, never files at the server's checkout.

The record is lossless and compact. Each document lists its element ids once, each URI is written once,
and the external references keep the export's order:

    {"schema": "de4sdv.export-documents/v1",
     "source_export_sha256": "<64 hex: the export file, as in served_model>",
     "element_count": <the elements the documents list>,
     "content_sha256": "sha256:<64 hex: documents_digest of the record>",
     "documents": {"<document path>": ["<element id>", ...]},
     "external_reference_uris": ["<uri>", ...],
     "external_references": [["<source element id>", "<property path>", "<target id>", <uri index>], ...]}

:func:`documents_digest` covers the schema, the export the record names, the element count and the
decoded values (element id -> document, and the external reference records in order). It is computed the
same way for an export and for a record, so a record equals an export's documents exactly when the two
digests agree. Loading recomputes it and refuses any difference, and refuses a URI that no reference uses.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .repository import element_id

EXPORT_DOCUMENTS_SCHEMA = "de4sdv.export-documents/v1"
#: The fields of an external reference record, as the export adapter writes them.
REFERENCE_FIELDS = ("source_element_id", "property_path", "target_id", "uri")
_KEYS = {"schema", "source_export_sha256", "element_count", "content_sha256", "documents",
         "external_reference_uris", "external_references"}
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def documents_digest(element_sources: Mapping[str, str], external_references: Iterable[Mapping[str, Any]], *,
                     source_export_sha256: str, schema: str = EXPORT_DOCUMENTS_SCHEMA) -> str:
    """``sha256:<hex>`` of the canonical JSON of the schema, the export file digest, the element count, the
    element sources (by id) and the external references (in order). The same for an export bundle and for
    the record of its documents."""
    payload = {"schema": schema, "source_export_sha256": source_export_sha256,
               "element_count": len(element_sources),
               "element_sources": {key: element_sources[key] for key in sorted(element_sources)},
               "external_references": [dict(record) for record in external_references]}
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _reference(record: Any) -> dict[str, str]:
    if (not isinstance(record, Mapping) or set(record) != set(REFERENCE_FIELDS)
            or not all(isinstance(record[name], str) for name in REFERENCE_FIELDS)):
        raise ValueError(f"export documents: an external reference must carry exactly the string fields "
                         f"{', '.join(REFERENCE_FIELDS)}, got {record!r}")
    return {name: record[name] for name in REFERENCE_FIELDS}


@dataclass(frozen=True, eq=False)
class ExportDocuments:
    """The source document of each element of one export, and its external references, as recorded."""

    source_export_sha256: str
    #: Element id -> its source document (read-only).
    element_sources: Mapping[str, str]
    #: The external reference records, in the export's order.
    external_references: tuple[dict[str, str], ...]
    content_sha256: str
    schema: str = EXPORT_DOCUMENTS_SCHEMA

    @property
    def element_count(self) -> int:
        return len(self.element_sources)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ExportDocuments):
            return NotImplemented
        return (self.schema, self.source_export_sha256, self.content_sha256) == (
            other.schema, other.source_export_sha256, other.content_sha256)

    def __hash__(self) -> int:
        return hash((self.schema, self.source_export_sha256, self.content_sha256))

    @classmethod
    def from_export(cls, bundle: Any, *, source_export_sha256: str) -> "ExportDocuments":
        """The record of an export bundle's element sources and external references (exactly, in order)."""
        if not _HEX64.fullmatch(str(source_export_sha256 or "")):
            raise ValueError("export documents: source_export_sha256 must be 64 lowercase hex digits")
        sources = dict(bundle.element_sources)
        if not sources or not all(isinstance(k, str) and k and isinstance(v, str) and v
                                  for k, v in sources.items()):
            raise ValueError("export documents: every element needs a source document, and there is at least one")
        references = tuple(_reference(record) for record in bundle.external_references)
        return cls(source_export_sha256=source_export_sha256, element_sources=MappingProxyType(sources),
                   external_references=references,
                   content_sha256=documents_digest(sources, references, source_export_sha256=source_export_sha256))

    @classmethod
    def from_dict(cls, value: object) -> "ExportDocuments":
        """Decode a recorded value; refuse any shape other than the writer's, and any digest difference."""
        if not isinstance(value, dict) or set(value) != _KEYS:
            raise ValueError(f"export_documents must carry exactly {', '.join(sorted(_KEYS))}")
        if value.get("schema") != EXPORT_DOCUMENTS_SCHEMA:
            raise ValueError(f"export_documents.schema must be {EXPORT_DOCUMENTS_SCHEMA}")
        if not _HEX64.fullmatch(str(value.get("source_export_sha256") or "")):
            raise ValueError("export_documents.source_export_sha256 must be 64 lowercase hex digits")
        if not _DIGEST.fullmatch(str(value.get("content_sha256") or "")):
            raise ValueError("export_documents.content_sha256 must be sha256:<64 lowercase hex>")
        count = value.get("element_count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise ValueError("export_documents.element_count must be a positive integer")
        documents = value.get("documents")
        if not isinstance(documents, dict) or not documents:
            raise ValueError("export_documents.documents must map each document to its element ids")
        sources: dict[str, str] = {}
        for document, identifiers in documents.items():
            if (not isinstance(document, str) or not document or not isinstance(identifiers, list)
                    or not identifiers or not all(isinstance(i, str) and i for i in identifiers)):
                raise ValueError("export_documents.documents must map each document to a non-empty list of ids")
            for identifier in identifiers:
                if identifier in sources:
                    raise ValueError(f"export_documents lists the element {identifier!r} more than once")
                sources[identifier] = document
        if len(sources) != count:
            raise ValueError(f"export_documents lists {len(sources)} elements, its element_count says {count}")
        uris = value.get("external_reference_uris")
        if not isinstance(uris, list) or not all(isinstance(u, str) for u in uris) or len(set(uris)) != len(uris):
            raise ValueError("export_documents.external_reference_uris must be a list of distinct strings")
        rows = value.get("external_references")
        if not isinstance(rows, list):
            raise ValueError("export_documents.external_references must be a list")
        references = []
        for row in rows:
            if (not isinstance(row, list) or len(row) != 4 or not all(isinstance(item, str) for item in row[:3])
                    or not isinstance(row[3], int) or isinstance(row[3], bool) or not 0 <= row[3] < len(uris)):
                raise ValueError("export_documents.external_references rows must be "
                                 "[source element id, property path, target id, uri index]")
            references.append(dict(zip(REFERENCE_FIELDS, (row[0], row[1], row[2], uris[row[3]]))))
        if len({row[3] for row in rows}) != len(uris):
            raise ValueError("export_documents.external_reference_uris lists a URI that no reference uses")
        actual = documents_digest(sources, references, source_export_sha256=value["source_export_sha256"])
        if actual != value["content_sha256"]:
            raise ValueError(f"export_documents content is {actual}, its record says {value['content_sha256']}")
        return cls(source_export_sha256=value["source_export_sha256"], element_sources=MappingProxyType(sources),
                   external_references=tuple(references), content_sha256=actual)

    def to_dict(self) -> dict[str, Any]:
        documents: dict[str, list[str]] = {}
        for identifier, document in self.element_sources.items():
            documents.setdefault(document, []).append(identifier)
        uris = sorted({record["uri"] for record in self.external_references})
        index = {uri: position for position, uri in enumerate(uris)}
        return {
            "schema": self.schema,
            "source_export_sha256": self.source_export_sha256,
            "element_count": self.element_count,
            "content_sha256": self.content_sha256,
            "documents": {document: sorted(documents[document]) for document in sorted(documents)},
            "external_reference_uris": uris,
            "external_references": [[r["source_element_id"], r["property_path"], r["target_id"], index[r["uri"]]]
                                    for r in self.external_references],
        }

    def summary(self) -> dict[str, Any]:
        """What an ingestion report records about the record."""
        return {"content_sha256": self.content_sha256,
                "document_count": len(set(self.element_sources.values())),
                "element_count": self.element_count,
                "external_reference_count": len(self.external_references)}

    def problem_for(self, elements: Iterable[Any]) -> str | None:
        """Why the record is not the record of this corpus (None when it lists exactly its element ids)."""
        served = {identifier for item in elements if isinstance(item, Mapping)
                  if (identifier := element_id(item))}
        recorded = set(self.element_sources)
        if served == recorded:
            return None
        return (f"the export documents do not cover the served corpus: {len(served - recorded)} served "
                f"element(s) without a recorded document, {len(recorded - served)} recorded element(s) not served")


__all__ = ["EXPORT_DOCUMENTS_SCHEMA", "ExportDocuments", "REFERENCE_FIELDS", "documents_digest"]
