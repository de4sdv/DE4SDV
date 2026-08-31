#!/usr/bin/env python3
"""Seed and verify the bounded AEBS impact fixture in a live SysML v2 API."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.sysml_api.client import ApiClient
from de4sdv.sysml_api.fixture import (
    ImpactFixture,
    aebs_impact_fixture,
    commit_payload,
)
from de4sdv.sysml_api.repository import element_id, reference_ids
from de4sdv.sysml_api.revisions import RevisionBinding


def semantic_key(element: dict[str, Any]) -> tuple[str, str]:
    return (
        str(element.get("@type") or ""),
        str(element.get("declaredName") or element.get("name") or ""),
    )


def ensure_project(client: ApiClient, name: str) -> dict[str, Any]:
    projects = client.get_all("/projects")
    for project in projects:
        if isinstance(project, dict) and project.get("name") == name:
            return project
    value = client.request(
        "POST",
        "/projects",
        {
            "@type": "Project",
            "name": name,
            "description": (
                "DE4SDV bounded AEBS semantic-impact API integration fixture."
            ),
        },
    )
    if not isinstance(value, dict):
        raise RuntimeError("project creation returned no JSON object")
    return value


def observed_id_map(
    expected: list[dict[str, Any]], observed: list[dict[str, Any]]
) -> dict[str, str]:
    observed_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for element in observed:
        observed_by_key.setdefault(semantic_key(element), []).append(element)
    result: dict[str, str] = {}
    for element in expected:
        matches = observed_by_key.get(semantic_key(element), [])
        if len(matches) != 1:
            raise RuntimeError(
                f"expected exactly one live API object for {semantic_key(element)}, "
                f"observed {len(matches)}"
            )
        expected_id = element_id(element)
        actual_id = element_id(matches[0])
        if expected_id is None or actual_id is None:
            raise RuntimeError("fixture or observed API object has no UUID")
        result[expected_id] = actual_id
    return result


def remap_references(payload: dict[str, Any], id_map: dict[str, str]) -> dict[str, Any]:
    value = json.loads(json.dumps(payload))

    def visit(item: Any) -> Any:
        if isinstance(item, dict):
            return {
                key: (
                    id_map.get(str(child), str(child))
                    if key in {"@id", "elementId"} and child is not None
                    else visit(child)
                )
                for key, child in item.items()
            }
        if isinstance(item, list):
            return [visit(child) for child in item]
        return item

    remapped = visit(value)
    if not isinstance(remapped, dict):
        raise TypeError("remapped payload is not an object")
    return remapped


def post_commit(
    client: ApiClient,
    project_id: str,
    fixture: ImpactFixture,
    elements: list[dict[str, Any]],
    name: str,
) -> str:
    value = client.request(
        "POST",
        f"/projects/{project_id}/commits",
        commit_payload(fixture, elements, name=name),
    )
    if not isinstance(value, dict) or element_id(value) is None:
        raise RuntimeError(f"commit {name!r} returned no API UUID")
    return str(element_id(value))


def validate_live_graph(
    elements: list[dict[str, Any]], fixture: ImpactFixture
) -> dict[str, int]:
    by_key = {semantic_key(item): item for item in elements}
    expected = list(fixture.elements.values())
    expected_by_key = {semantic_key(item): item for item in expected}
    missing = sorted(set(expected_by_key) - set(by_key))
    if missing:
        raise RuntimeError(f"live API graph is missing fixture objects: {missing}")

    root = by_key[("RequirementUsage", "reqCommandEmergencyBraking")]
    member = by_key[("PartUsage", "memberProduct")]
    if reference_ids(root.get("subjectParameter")) != [element_id(member)]:
        raise RuntimeError("live requirement subjectParameter was not preserved")

    evidence_ids = {
        element_id(by_key[("RequirementUsage", name)])
        for name in (
            "evidenceContract009BFreshOverrideClear",
            "evidenceContract009BNominalBrakingPath",
            "evidenceContract009CMRMGateChain",
        )
    }
    verification_refs = set()
    for name in (
        "nominalMovingVehicleTargetVerification009B",
        "nativeInterventionToMRMVerification009C",
    ):
        verification_refs.update(
            reference_ids(by_key[("VerificationCaseUsage", name)].get("verifiedRequirement"))
        )
    if verification_refs != evidence_ids:
        raise RuntimeError("live verification-to-evidence references were not preserved")

    root_id = element_id(root)
    dependencies = [item for item in elements if item.get("@type") == "Dependency"]
    relevant = [
        item
        for item in dependencies
        if root_id in reference_ids(item.get("target"))
        and set(reference_ids(item.get("source"))) <= evidence_ids
    ]
    if len(relevant) != 3:
        raise RuntimeError(
            f"expected 3 live evidence relevance dependencies, observed {len(relevant)}"
        )
    return {
        "elements": len(elements),
        "evidence_contracts": len(evidence_ids),
        "verification_cases": 2,
        "relevance_dependencies": len(relevant),
    }


def seed(
    client: ApiClient,
    fixture: ImpactFixture,
    *,
    project_name: str,
) -> tuple[str, str, dict[str, int]]:
    project = ensure_project(client, project_name)
    project_id = element_id(project)
    if project_id is None:
        raise RuntimeError("project has no API UUID")
    fixture_elements = list(fixture.elements.values())

    stage_one = [
        item
        for item in fixture_elements
        if item["@type"] in {"RequirementDefinition", "PartUsage"}
        or (
            item["@type"] == "RequirementUsage"
            and item["declaredName"] != "reqCommandEmergencyBraking"
        )
    ]
    commit_one = post_commit(
        client, project_id, fixture, stage_one, "seed AEBS impact fixture nodes"
    )
    observed_one = client.get_all(
        f"/projects/{project_id}/commits/{commit_one}/elements"
    )
    id_map = observed_id_map(stage_one, observed_one)

    stage_two_source = [
        item
        for item in fixture_elements
        if item["@type"] == "VerificationCaseUsage"
        or item.get("declaredName") == "reqCommandEmergencyBraking"
    ]
    stage_two = [remap_references(item, id_map) for item in stage_two_source]
    commit_two = post_commit(
        client, project_id, fixture, stage_two, "link AEBS requirement and verification"
    )
    observed_two = client.get_all(
        f"/projects/{project_id}/commits/{commit_two}/elements"
    )
    id_map.update(observed_id_map(stage_two_source, observed_two))

    stage_three_source = [item for item in fixture_elements if item["@type"] == "Dependency"]
    stage_three = [remap_references(item, id_map) for item in stage_three_source]
    commit_three = post_commit(
        client, project_id, fixture, stage_three, "link AEBS relevance dependencies"
    )
    observed_final = client.get_all(
        f"/projects/{project_id}/commits/{commit_three}/elements"
    )
    summary = validate_live_graph(observed_final, fixture)
    return project_id, commit_three, summary


def git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:9000")
    parser.add_argument("--project-name", default="DE4SDV AEBS API Impact Pilot")
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--git-commit", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture = aebs_impact_fixture()
    project_id, commit_id, summary = seed(
        ApiClient(args.api_url), fixture, project_name=args.project_name
    )
    binding = RevisionBinding(
        git_repository="DE4SDV",
        git_commit=args.git_commit or git_head(),
        sysml_project_id=project_id,
        sysml_commit_id=commit_id,
        import_timestamp=datetime.now(timezone.utc).isoformat(),
        import_tool_version="de4sdv-aebs-api-fixture/1",
        semantic_validation="passed",
        scope="AEBS impact pilot fixture",
    )
    args.binding.parent.mkdir(parents=True, exist_ok=True)
    args.binding.write_text(json.dumps(binding.to_dict(), indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "project_id": project_id,
                "commit_id": commit_id,
                "binding": str(args.binding),
                "validation": summary,
                "source_files": list(fixture.source_files),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
