"""Served-model digest: one content identity for an export and an API listing.

The deployment imports the validated licensed export into its Systems
Modeling API repository. The pinned API returns every exported element with
all of its fields unchanged and pads it with further schema fields that carry
no value (``null``, an empty list, an empty object or an empty string).

:func:`served_model_digest` is computed the same way over both forms: each
element drops its top-level fields that carry no value, is serialized as
canonical JSON and digested; the per-element digests are then digested in
element-id order. Numbers compare by value: an integral float is written as
the integer (the export writes a ``LiteralRational`` value as ``0``, the
pinned API as ``0.0``); booleans stay booleans. Two corpora have the same
digest exactly when they hold the same element ids with the same carried
field values, regardless of listing order or valueless padding.

The importer records the digest in the revision binding
(:class:`ServedModel`, ``served_model``) after verifying that the API read-back
equals the export element by element. The runtime recomputes it over the
corpus it serves and refuses to answer from any other corpus.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .repository import element_id

SERVED_MODEL_SCHEMA = "de4sdv.served-model/v1"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def _carries_value(value: Any) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, (list, dict)) and not value:
        return False
    return True


def normalized_element(element: Mapping[str, Any]) -> dict[str, Any]:
    """The element without its top-level fields that carry no value."""
    return {key: value for key, value in element.items() if _carries_value(value)}


def _numbers_by_value(value: Any) -> Any:
    """Integral floats as integers, recursively (booleans are not numbers here)."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {key: _numbers_by_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_numbers_by_value(item) for item in value]
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(_numbers_by_value(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _element_digest(element: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(normalized_element(element))).hexdigest()


def element_digests(elements: Iterable[Any]) -> dict[str, str]:
    """Element id -> sha256 of its normalized canonical JSON (fail closed)."""
    digests: dict[str, str] = {}
    for index, element in enumerate(elements):
        if not isinstance(element, Mapping):
            raise ValueError(f"served-model element {index} is not a JSON object")
        identifier = element_id(element)
        if not identifier:
            raise ValueError(f"served-model element {index} has no element id")
        if identifier in digests:
            raise ValueError(f"served-model corpus has a duplicate element id {identifier!r}")
        digests[identifier] = _element_digest(element)
    if not digests:
        raise ValueError("served-model corpus is empty")
    return digests


def digest_of_element_digests(digests: Mapping[str, str]) -> str:
    """The corpus digest over per-element digests, in element-id order."""
    combined = hashlib.sha256()
    for identifier in sorted(digests):
        combined.update(f"{identifier}\t{digests[identifier]}\n".encode("utf-8"))
    return "sha256:" + combined.hexdigest()


def served_model_digest(elements: Iterable[Any]) -> str:
    """``sha256:<hex>`` content identity of one element corpus."""
    return digest_of_element_digests(element_digests(elements))


def payload_differences(expected: Mapping[str, Mapping[str, Any]],
                        actual: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """Ids present in both corpora whose carried field values differ.

    Compared exactly as :func:`served_model_digest` compares them.
    """
    return sorted(identifier for identifier in set(expected) & set(actual)
                  if _element_digest(expected[identifier]) != _element_digest(actual[identifier]))


@dataclass(frozen=True)
class ServedModel:
    """The validated export a deployment serves, as recorded at import."""

    source_export_sha256: str
    element_count: int
    content_sha256: str
    schema: str = SERVED_MODEL_SCHEMA

    @classmethod
    def from_dict(cls, value: object) -> "ServedModel":
        if not isinstance(value, dict):
            raise ValueError("served_model must be a JSON object")
        expected = {"schema", "source_export_sha256", "element_count", "content_sha256"}
        if set(value) != expected:
            raise ValueError("served_model must carry exactly schema, source_export_sha256, "
                             "element_count and content_sha256")
        if value.get("schema") != SERVED_MODEL_SCHEMA:
            raise ValueError(f"served_model.schema must be {SERVED_MODEL_SCHEMA}")
        if not _HEX64.fullmatch(str(value.get("source_export_sha256") or "")):
            raise ValueError("served_model.source_export_sha256 must be 64 lowercase hex digits")
        count = value.get("element_count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise ValueError("served_model.element_count must be a positive integer")
        if not _DIGEST.fullmatch(str(value.get("content_sha256") or "")):
            raise ValueError("served_model.content_sha256 must be sha256:<64 lowercase hex>")
        return cls(source_export_sha256=value["source_export_sha256"], element_count=count,
                   content_sha256=value["content_sha256"])

    @classmethod
    def from_elements(cls, elements: Iterable[Any], *, source_export_sha256: str) -> "ServedModel":
        digests = element_digests(elements)
        return cls.from_dict({"schema": SERVED_MODEL_SCHEMA,
                              "source_export_sha256": source_export_sha256,
                              "element_count": len(digests),
                              "content_sha256": digest_of_element_digests(digests)})

    def to_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, "source_export_sha256": self.source_export_sha256,
                "element_count": self.element_count, "content_sha256": self.content_sha256}


__all__ = ["SERVED_MODEL_SCHEMA", "ServedModel", "digest_of_element_digests", "element_digests",
           "normalized_element", "payload_differences", "served_model_digest"]
