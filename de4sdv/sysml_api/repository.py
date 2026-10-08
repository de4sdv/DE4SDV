"""Higher-level revision-scoped SysML semantic repository interface."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from .client import ApiClient
from .errors import ApiError

Direction = Literal["incoming", "outgoing", "both"]

#: Lazy corpus source: (project_id, commit_id) -> elements or None on miss.
CorpusSource = Callable[[str, str], "list[dict[str, Any]] | None"]
#: Best-effort corpus sink invoked after an authoritative retrieval.
CorpusSink = Callable[[str, str, "list[dict[str, Any]]"], None]


def element_id(value: object) -> str | None:
    """Return the identifier carried by a SysML API element or reference."""
    if not isinstance(value, dict):
        return None
    candidate = value.get("@id") or value.get("elementId") or value.get("id")
    return str(candidate) if candidate is not None else None


def validated_element_corpus(value: object) -> list[dict[str, Any]]:
    """Structurally validate an element listing (fail closed).

    The explicit adoption path for the persistent corpus cache must never
    accept a malformed, truncated, or partially overlapping corpus: a value
    that is not a non-empty list of JSON objects carrying unique element
    UUIDs is refused entirely — never partially adopted, never silently
    repaired. Callers treat a refusal as a cache miss and fall back to the
    exact API load.
    """
    if not isinstance(value, list) or not value:
        raise ValueError("element corpus must be a non-empty list")
    seen: set[str] = set()
    validated: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"element corpus item {index} is not a JSON object")
        candidate_id = element_id(item)
        if candidate_id is None:
            raise ValueError(f"element corpus item {index} has no element UUID")
        if candidate_id in seen:
            raise ValueError(
                f"element corpus item {index} duplicates element UUID "
                f"{candidate_id!r}"
            )
        seen.add(candidate_id)
        validated.append(item)
    return validated


def reference_ids(value: object) -> list[str]:
    if isinstance(value, dict):
        candidate = element_id(value)
        return [candidate] if candidate else []
    if not isinstance(value, list):
        return []
    return [candidate for item in value if (candidate := element_id(item)) is not None]


@dataclass
class SysMLRepository:
    """Read-only semantic access pinned by project and commit identifiers.

    API commits are immutable, so element listings are memoized per
    (project, commit) revision to avoid repeated full-model fetches within one
    process. One retrieval per revision is guaranteed even under concurrent
    first calls (``_lock``).

    A lazy corpus source/sink pair may be installed (see
    :meth:`install_corpus_source`): the source is consulted BEFORE the
    network on the first listing of a revision (persistent corpus cache),
    and the sink receives the authoritative result afterwards for a
    best-effort write-back. The source is never trusted by itself: the
    corpus it returns is structurally validated before adoption, and the
    caller is responsible for identity binding.
    """

    client: ApiClient
    _element_cache: dict[tuple[str, str], list[dict[str, Any]]] = field(
        default_factory=dict, repr=False, compare=False
    )
    _lock: threading.Lock = field(
        default_factory=threading.Lock, repr=False, compare=False
    )
    _corpus_source: CorpusSource | None = field(
        default=None, init=False, repr=False, compare=False
    )
    _corpus_sink: CorpusSink | None = field(
        default=None, init=False, repr=False, compare=False
    )

    def install_corpus_source(
        self, source: CorpusSource, *, sink: CorpusSink | None = None
    ) -> None:
        """Install the lazy snapshot-first corpus hook (idempotent).

        Installing performs no I/O: server handshakes must never block on a
        cold load. The hook runs on the first listing of a revision only.
        """
        self._corpus_source = source
        self._corpus_sink = sink

    def adopt_elements(
        self, project_id: str, commit_id: str, elements: object
    ) -> bool:
        """Adopt a structurally validated external element listing.

        Explicit hydration path for the persistent corpus snapshot (and for
        tests): the caller has already bound the payload identity to this
        exact revision; this method re-validates the payload shape (fail
        closed on malformed items, missing UUIDs, duplicates) and refuses to
        displace a listing already loaded from the authoritative API in this
        process. Returns ``True`` when adopted.
        """
        validated = validated_element_corpus(elements)
        cache_key = (project_id, commit_id)
        with self._lock:
            if cache_key in self._element_cache:
                return False
            self._element_cache[cache_key] = validated
        return True

    def get_project(self, project_id: str) -> dict[str, Any]:
        value = self.client.request("GET", f"/projects/{project_id}")
        if not isinstance(value, dict):
            raise ApiError("GET", f"/projects/{project_id}", "expected a JSON object")
        return value

    def get_commit(self, project_id: str, commit_id: str) -> dict[str, Any]:
        path = f"/projects/{project_id}/commits/{commit_id}"
        value = self.client.request("GET", path)
        if not isinstance(value, dict):
            raise ApiError("GET", path, "expected a JSON object")
        return value

    def get_element(
        self, project_id: str, commit_id: str, element_id_value: str
    ) -> dict[str, Any]:
        path = (
            f"/projects/{project_id}/commits/{commit_id}/elements/"
            f"{element_id_value}"
        )
        value = self.client.request("GET", path)
        if not isinstance(value, dict):
            raise ApiError("GET", path, "expected a JSON object")
        return value

    def list_elements(self, project_id: str, commit_id: str) -> list[dict[str, Any]]:
        cache_key = (project_id, commit_id)
        cached = self._element_cache.get(cache_key)
        if cached is not None:
            return cached
        with self._lock:
            # One retrieval per revision per process, even under concurrent
            # first calls: the double-check keeps the cold load single.
            cached = self._element_cache.get(cache_key)
            if cached is not None:
                return cached
            if self._corpus_source is not None:
                # Snapshot-first (persistent corpus cache). The source is
                # responsible for exact-revision identity binding; a miss
                # (None) falls through to the authoritative API load.
                snapshot = self._corpus_source(project_id, commit_id)
                if snapshot is not None:
                    self._element_cache[cache_key] = validated_element_corpus(
                        snapshot
                    )
                    return self._element_cache[cache_key]
            path = f"/projects/{project_id}/commits/{commit_id}/elements?page[size]=1000"
            values = self.client.get_all(path)
            if not all(isinstance(value, dict) for value in values):
                raise ApiError("GET", path, "element page contained a non-object value")
            self._element_cache[cache_key] = values
        if self._corpus_sink is not None:
            # Best-effort write-back; a cache failure is never a query failure.
            self._corpus_sink(project_id, commit_id, values)
        return values

    def check_capabilities(self, project_id: str, commit_id: str) -> dict[str, Any]:
        """Exercise the read contract required by semantic impact queries."""
        self.get_project(project_id)
        self.get_commit(project_id, commit_id)
        elements = self.list_elements(project_id, commit_id)
        return {
            "project_read": True,
            "commit_read": True,
            "element_read": True,
            "semantic_types": sorted(
                {str(item["@type"]) for item in elements if item.get("@type")}
            ),
        }

    def relationships(
        self,
        project_id: str,
        commit_id: str,
        element_id_value: str,
        direction: Direction = "both",
    ) -> list[dict[str, Any]]:
        """Return API relationship elements incident on one exact element UUID.

        Direction follows the native ``source``/``target`` relationship object;
        ``client``/``supplier`` are accepted as the Dependency aliases observed
        by the PR #36 live-service challenge.
        """
        if direction not in {"incoming", "outgoing", "both"}:
            raise ValueError(f"unsupported relationship direction: {direction}")
        matches: list[dict[str, Any]] = []
        for candidate in self.list_elements(project_id, commit_id):
            source_ids = set(
                reference_ids(candidate.get("source"))
                + reference_ids(candidate.get("client"))
            )
            target_ids = set(
                reference_ids(candidate.get("target"))
                + reference_ids(candidate.get("supplier"))
            )
            outgoing = element_id_value in source_ids
            incoming = element_id_value in target_ids
            if (
                (direction == "outgoing" and outgoing)
                or (direction == "incoming" and incoming)
                or (direction == "both" and (outgoing or incoming))
            ):
                matches.append(candidate)
        return matches
