"""Higher-level revision-scoped SysML semantic repository interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .client import ApiClient
from .errors import ApiError

Direction = Literal["incoming", "outgoing", "both"]


def element_id(value: object) -> str | None:
    """Return the identifier carried by a SysML API element or reference."""
    if not isinstance(value, dict):
        return None
    candidate = value.get("@id") or value.get("elementId") or value.get("id")
    return str(candidate) if candidate is not None else None


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
    process.
    """

    client: ApiClient
    _element_cache: dict[tuple[str, str], list[dict[str, Any]]] = field(
        default_factory=dict, repr=False, compare=False
    )

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
        if cache_key not in self._element_cache:
            path = f"/projects/{project_id}/commits/{commit_id}/elements?page[size]=1000"
            values = self.client.get_all(path)
            if not all(isinstance(value, dict) for value in values):
                raise ApiError("GET", path, "element page contained a non-object value")
            self._element_cache[cache_key] = values
        return self._element_cache[cache_key]

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
