"""Production import adapter for official SysML JSON exports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .baseline import BaselineExportBundle
from .errors import BaselineImportError
from .performance import timing
from .repository import element_id


@dataclass(frozen=True)
class BaselineImportResult:
    project_id: str
    commit_id: str
    element_count: int
    internal_reference_count: int
    # Only populated after complete identity and required-reference verification.
    # Reuse is confined to this newly imported immutable project/commit.
    readback_elements: tuple[dict[str, Any], ...]


def baseline_commit_payload(
    elements: dict[str, dict[str, Any]], *, git_commit: str
) -> dict[str, Any]:
    """Build one immutable baseline commit while preserving exporter UUIDs."""
    return {
        "@type": "Commit",
        "name": f"DE4SDV baseline {git_commit[:12]}",
        "description": f"Reviewed DE4SDV SysML baseline at Git {git_commit}",
        "change": [
            {
                "@type": "DataVersion",
                "identity": {"@id": element_id},
                "payload": element,
            }
            for element_id, element in elements.items()
        ],
    }


def import_baseline(
    client: Any,
    bundle: BaselineExportBundle,
    *,
    project_name: str,
) -> BaselineImportResult:
    """Create an immutable project/commit and verify exact UUID/ref readback."""
    project = client.request(
        "POST",
        "/projects",
        {
            "@type": "Project",
            "name": project_name,
            "description": (
                "Reviewed DE4SDV full SysML baseline imported from Git "
                f"{bundle.git_commit}"
            ),
        },
    )
    project_id = element_id(project)
    if project_id is None:
        raise BaselineImportError("API project response did not contain an identity")
    with timing("commit_payload", elements=len(bundle.elements)):
        payload = baseline_commit_payload(bundle.elements, git_commit=bundle.git_commit)
    with timing("baseline_post"):
        commit = client.request("POST", f"/projects/{project_id}/commits", payload)
    del payload
    commit_id = element_id(commit)
    if commit_id is None:
        raise BaselineImportError("API commit response did not contain an identity")
    path = f"/projects/{project_id}/commits/{commit_id}/elements"
    values = client.get_all(path)
    if not all(isinstance(value, dict) for value in values):
        raise BaselineImportError("API readback contained a non-object element")
    readback = {
        candidate_id: value
        for value in values
        if (candidate_id := element_id(value)) is not None
    }
    if len(readback) != len(values):
        raise BaselineImportError("API readback contained missing or duplicate element identities")
    expected_ids = set(bundle.elements)
    actual_ids = set(readback)
    if expected_ids != actual_ids:
        missing = sorted(expected_ids - actual_ids)
        unexpected = sorted(actual_ids - expected_ids)
        raise BaselineImportError(
            f"API element identity readback mismatch: missing={missing[:20]}, "
            f"unexpected={unexpected[:20]}"
        )
    with timing("internal_reference_comparison") as metrics:
        expected_refs = _reference_paths(bundle.elements)
        actual_refs = _reference_paths(readback)
        metrics["expected_references"] = len(expected_refs)
        metrics["actual_references"] = len(actual_refs)
        lost_refs = sorted(expected_refs - actual_refs)
        if lost_refs:
            raise BaselineImportError(
                f"API readback lost {len(lost_refs)} internal references: {lost_refs[:20]}"
            )
    return BaselineImportResult(
        project_id=project_id,
        commit_id=commit_id,
        element_count=len(readback),
        internal_reference_count=len(expected_refs),
        readback_elements=tuple(values),
    )


def _reference_paths(
    elements: dict[str, dict[str, Any]],
) -> set[tuple[str, str, str]]:
    references: set[tuple[str, str, str]] = set()
    known_ids = set(elements)
    for source_id, value in elements.items():
        _collect_reference_paths(
            value,
            source_id=source_id,
            path="",
            known_ids=known_ids,
            references=references,
        )
    return references


def _collect_reference_paths(
    value: Any,
    *,
    source_id: str,
    path: str,
    known_ids: set[str],
    references: set[tuple[str, str, str]],
) -> None:
    if isinstance(value, dict):
        if "@id" in value and "@type" not in value:
            target_id = value.get("@id")
            if isinstance(target_id, str) and target_id in known_ids:
                references.add((source_id, path, target_id))
            return
        for key, item in value.items():
            child_path = f"{path}.{key}" if path else key
            _collect_reference_paths(
                item,
                source_id=source_id,
                path=child_path,
                known_ids=known_ids,
                references=references,
            )
    elif isinstance(value, list):
        for item in value:
            _collect_reference_paths(
                item,
                source_id=source_id,
                path=path,
                known_ids=known_ids,
                references=references,
            )
