#!/usr/bin/env python3
"""SysML v2 API challenge harness for the DE4SDV pilot.

The harness treats the SysML v2 API repository as the system under test.  It
seeds a small DE4SDV context graph, reads back the graph that the API exposes,
and emits an evidence report describing which SysML/API capabilities were
exercised and which gaps remain.

It intentionally does not talk to SysON. SysON should become a tool adapter into
this API-centered loop, not the live source of truth for this challenge.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_API_URL = "http://127.0.0.1:9000"
DEFAULT_PROJECT = "DE4SDV API Challenge"
DEFAULT_REPORT = Path("sysmlv2-api/challenge-reports/de4sdv-context-api-challenge.json")


@dataclass(frozen=True)
class ChallengeModel:
    """Expected DE4SDV model slice used to challenge the SysML v2 API."""

    name: str
    description: str
    elements: dict[str, dict[str, Any]]
    capabilities: list[str]
    gap_questions: list[dict[str, str]]


@dataclass(frozen=True)
class ApiClient:
    base_url: str

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def request(self, method: str, path: str, payload: Any | None = None) -> Any:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self._url(path), data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {path} failed with HTTP {exc.code}: {body[:2000]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"{method} {path} failed: {exc.reason}") from exc
        if not raw:
            return None
        return json.loads(raw)


def ref(element_id: str) -> dict[str, str]:
    return {"@id": element_id}


def base_element(element_type: str, element_id: str, name: str, *, owner_id: str | None = None) -> dict[str, Any]:
    owner = ref(owner_id) if owner_id else None
    return {
        "@type": element_type,
        "@id": element_id,
        "aliasIds": [],
        "declaredName": name,
        "declaredShortName": None,
        "documentation": [],
        "elementId": element_id,
        "isImpliedIncluded": False,
        "isLibraryElement": False,
        "name": name,
        "ownedAnnotation": [],
        "ownedElement": [],
        "ownedRelationship": [],
        "owner": owner,
        "owningMembership": None,
        "owningNamespace": owner,
        "owningRelationship": None,
        "qualifiedName": name if owner_id is None else None,
        "shortName": None,
        "textualRepresentation": [],
    }


def package(element_id: str, name: str, *, owner_id: str | None = None, owned_ids: list[str] | None = None) -> dict[str, Any]:
    element = base_element("Package", element_id, name, owner_id=owner_id)
    owned = [ref(item) for item in owned_ids or []]
    element.update(
        {
            "filterCondition": [],
            "importedMembership": [],
            "member": owned,
            "membership": [],
            "ownedImport": [],
            "ownedMember": owned,
            "ownedMembership": [],
        }
    )
    return element


def part_def(element_id: str, name: str, *, owner_id: str) -> dict[str, Any]:
    element = base_element("PartDefinition", element_id, name, owner_id=owner_id)
    element.update(
        {
            "feature": [],
            "inheritedMembership": [],
            "input": [],
            "isAbstract": False,
            "isVariation": False,
            "membership": [],
            "ownedFeature": [],
            "ownedMembership": [],
            "ownedUsage": [],
            "output": [],
        }
    )
    return element


def part_usage(element_id: str, name: str, *, owner_id: str, definition_id: str, is_reference: bool = False) -> dict[str, Any]:
    element = base_element("PartUsage", element_id, name, owner_id=owner_id)
    element.update(
        {
            "definition": ref(definition_id),
            "isReference": is_reference,
            "isVariation": False,
            "ownedFeature": [],
            "ownedMembership": [],
            "typing": [ref(definition_id)],
        }
    )
    return element


def dependency(element_id: str, name: str, *, owner_id: str, source_id: str, target_id: str) -> dict[str, Any]:
    element = base_element("Dependency", element_id, name, owner_id=owner_id)
    element.update(
        {
            "client": [ref(source_id)],
            "supplier": [ref(target_id)],
            "source": [ref(source_id)],
            "target": [ref(target_id)],
        }
    )
    return element


def context_challenge_model() -> ChallengeModel:
    root = "de4sdv-root"
    context = "de4sdv-context"
    assets = "de4sdv-engineering-assets"
    relationships = "de4sdv-relationship-intents"
    product_line = "de4sdv-context-configurable-sdv-product-line"
    lifecycle = "de4sdv-context-lifecycle-engineering-system"
    ecosystem = "de4sdv-context-open-innovation-ecosystem"
    model_repo = "de4sdv-asset-model-repository"
    validation = "de4sdv-asset-validation-pipeline"
    evidence = "de4sdv-asset-evidence-baseline"

    elements: dict[str, dict[str, Any]] = {
        root: package(root, "DE4SDV", owned_ids=[context, assets, relationships]),
        context: package(context, "Context", owner_id=root, owned_ids=[product_line, lifecycle, ecosystem]),
        assets: package(assets, "EngineeringAssets", owner_id=root, owned_ids=[model_repo, validation, evidence]),
        relationships: package(
            relationships,
            "RelationshipIntents",
            owner_id=root,
            owned_ids=[
                "de4sdv-relationship-governs-evolves",
                "de4sdv-relationship-engineers-assures",
                "de4sdv-relationship-manages-model-baselines",
                "de4sdv-relationship-executes-validation",
                "de4sdv-relationship-maintains-assurance-evidence",
            ],
        ),
        product_line: part_def(product_line, "ConfigurableSDVProductLine", owner_id=context),
        lifecycle: part_def(lifecycle, "LifecycleEngineeringSystem", owner_id=context),
        ecosystem: part_def(ecosystem, "OpenInnovationEcosystem", owner_id=context),
        model_repo: part_def(model_repo, "ModelRepository", owner_id=assets),
        validation: part_def(validation, "ValidationPipeline", owner_id=assets),
        evidence: part_def(evidence, "EvidenceBaseline", owner_id=assets),
        "de4sdv-usage-engineered-product-line": part_usage(
            "de4sdv-usage-engineered-product-line",
            "engineeredProductLine",
            owner_id=lifecycle,
            definition_id=product_line,
            is_reference=True,
        ),
        "de4sdv-usage-model-repository": part_usage(
            "de4sdv-usage-model-repository",
            "modelRepository",
            owner_id=lifecycle,
            definition_id=model_repo,
        ),
        "de4sdv-usage-validation-pipeline": part_usage(
            "de4sdv-usage-validation-pipeline",
            "validationPipeline",
            owner_id=lifecycle,
            definition_id=validation,
        ),
        "de4sdv-usage-evidence-baseline": part_usage(
            "de4sdv-usage-evidence-baseline",
            "evidenceBaseline",
            owner_id=lifecycle,
            definition_id=evidence,
        ),
        "de4sdv-usage-governed-lifecycle-system": part_usage(
            "de4sdv-usage-governed-lifecycle-system",
            "governedLifecycleSystem",
            owner_id=ecosystem,
            definition_id=lifecycle,
            is_reference=True,
        ),
        "de4sdv-relationship-governs-evolves": dependency(
            "de4sdv-relationship-governs-evolves",
            "governs / evolves",
            owner_id=relationships,
            source_id=ecosystem,
            target_id=lifecycle,
        ),
        "de4sdv-relationship-engineers-assures": dependency(
            "de4sdv-relationship-engineers-assures",
            "engineers / assures",
            owner_id=relationships,
            source_id=lifecycle,
            target_id=product_line,
        ),
        "de4sdv-relationship-manages-model-baselines": dependency(
            "de4sdv-relationship-manages-model-baselines",
            "manages model baselines",
            owner_id=relationships,
            source_id=lifecycle,
            target_id=model_repo,
        ),
        "de4sdv-relationship-executes-validation": dependency(
            "de4sdv-relationship-executes-validation",
            "executes validation",
            owner_id=relationships,
            source_id=lifecycle,
            target_id=validation,
        ),
        "de4sdv-relationship-maintains-assurance-evidence": dependency(
            "de4sdv-relationship-maintains-assurance-evidence",
            "maintains assurance evidence",
            owner_id=relationships,
            source_id=lifecycle,
            target_id=evidence,
        ),
    }
    return ChallengeModel(
        name="DE4SDV API context challenge",
        description="ASELCM System 1/2/3 context plus engineering asset relationships.",
        elements=elements,
        capabilities=[
            "Package containment",
            "PartDefinition",
            "PartUsage",
            "Reference PartUsage",
            "Dependency source/target relationships",
            "Project commit creation/readback",
            "Deterministic API evidence report",
        ],
        gap_questions=[
            {
                "capability": "diagram layout/view representation",
                "question": "Can the standard API carry enough view/layout semantics for SysON/Sirius diagrams, or must layout remain tool-specific publication state?",
                "impact": "Determines whether generated SVGs can be reproduced from API state alone.",
            },
            {
                "capability": "textual notation roundtrip",
                "question": "Can API state be exported to stable, reviewable SysML v2 textual notation without losing identifiers and relationship intent?",
                "impact": "Determines whether GitHub snapshots can be derived from API state instead of hand-maintained.",
            },
            {
                "capability": "branch and merge semantics",
                "question": "Can model commits support reviewable branch/merge workflows aligned with GitHub PRs?",
                "impact": "Determines whether API repository baselines can support open-source contribution flow.",
            },
        ],
    )


def commit_payload(model: ChallengeModel) -> dict[str, Any]:
    return {
        "@type": "Commit",
        "name": "seed DE4SDV API context challenge",
        "description": model.description,
        "change": [{"@type": "DataVersion", "payload": payload} for payload in model.elements.values()],
    }


def normalize_observed_elements(raw: Any) -> dict[str, dict[str, Any]]:
    """Convert common API readback shapes into an id -> element mapping."""
    observed: dict[str, dict[str, Any]] = {}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            element_id = value.get("@id") or value.get("elementId") or value.get("id")
            element_type = value.get("@type")
            if element_id and element_type:
                observed[str(element_id)] = value
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(raw)
    return observed


def _ids(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    ids = []
    for value in values:
        if isinstance(value, dict):
            candidate = value.get("@id") or value.get("id") or value.get("elementId")
            if candidate:
                ids.append(str(candidate))
    return ids


def compare_element(expected: dict[str, Any], observed: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    for key in ("@type", "name"):
        if observed.get(key) != expected.get(key):
            problems.append(f"{key} expected {expected.get(key)!r}, observed {observed.get(key)!r}")
    if expected.get("@type") == "Dependency":
        for key in ("source", "target"):
            if _ids(observed.get(key)) != _ids(expected.get(key)):
                problems.append(f"{key} expected {_ids(expected.get(key))!r}, observed {_ids(observed.get(key))!r}")
    if expected.get("@type") == "PartUsage":
        if observed.get("isReference") != expected.get("isReference"):
            problems.append(f"isReference expected {expected.get('isReference')!r}, observed {observed.get('isReference')!r}")
    return problems


def build_challenge_report(model: ChallengeModel, observed: dict[str, dict[str, Any]], *, source: str) -> dict[str, Any]:
    passed: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    for element_id, expected in model.elements.items():
        observed_element = observed.get(element_id)
        item = {"id": element_id, "type": expected["@type"], "name": expected.get("name", "")}
        if observed_element is None:
            failed.append({**item, "reason": "expected element missing from observed API graph"})
            continue
        problems = compare_element(expected, observed_element)
        if problems:
            failed.append({**item, "reason": "; ".join(problems)})
        else:
            passed.append(item)
    status = "passed" if not failed else "failed"
    return {
        "schema": "de4sdv.sysml-api-challenge-report.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "challenge": {"name": model.name, "description": model.description},
        "summary": {
            "status": status,
            "tested_elements": len(model.elements),
            "passed": len(passed),
            "failed": len(failed),
        },
        "capabilities": model.capabilities,
        "passed": passed,
        "failed": failed,
        "gap_questions": model.gap_questions,
    }


def find_project(client: ApiClient, name: str) -> dict[str, Any] | None:
    projects = client.request("GET", "/projects")
    for project in projects or []:
        if project.get("name") == name:
            return project
    return None


def ensure_project(client: ApiClient, name: str) -> dict[str, Any]:
    project = find_project(client, name)
    if project:
        return project
    return client.request(
        "POST",
        "/projects",
        {
            "@type": "Project",
            "name": name,
            "description": "DE4SDV SysML v2 API challenge project for exercising model repository semantics.",
        },
    )


def seed_context(client: ApiClient, project_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    model = context_challenge_model()
    project = ensure_project(client, project_name)
    commit = client.request("POST", f"/projects/{project['@id']}/commits", commit_payload(model))
    return project, commit


def read_commit_roots(client: ApiClient, project_id: str, commit_id: str) -> dict[str, dict[str, Any]]:
    roots = client.request("GET", f"/projects/{project_id}/commits/{commit_id}/roots")
    return normalize_observed_elements(roots)


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")


def command_dry_run(args: argparse.Namespace) -> int:
    model = context_challenge_model()
    report = build_challenge_report(model, model.elements, source="dry-run expected graph")
    write_report(args.output, report)
    print(f"wrote dry-run challenge report: {args.output}")
    return 0 if report["summary"]["status"] == "passed" else 1


def command_seed_context(args: argparse.Namespace) -> int:
    client = ApiClient(args.api_url)
    project, commit = seed_context(client, args.project)
    observed = read_commit_roots(client, project["@id"], commit["@id"])
    report = build_challenge_report(context_challenge_model(), observed, source=f"{args.api_url} commit {commit['@id']}")
    report["api"] = {"url": args.api_url, "project_id": project["@id"], "commit_id": commit["@id"]}
    write_report(args.output, report)
    print(f"seeded project {project['@id']} commit {commit['@id']}")
    print(f"wrote challenge report: {args.output}")
    return 0 if report["summary"]["status"] == "passed" else 2


def command_export_expected(args: argparse.Namespace) -> int:
    model = context_challenge_model()
    payload = {"name": model.name, "description": model.description, "elements": list(model.elements.values())}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote expected API graph: {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    dry_run = sub.add_parser("dry-run", help="write an expected-graph report without contacting an API server")
    dry_run.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    dry_run.set_defaults(func=command_dry_run)

    seed = sub.add_parser("seed-context", help="seed the challenge graph into a SysML v2 API server and compare readback")
    seed.add_argument("--api-url", default=DEFAULT_API_URL)
    seed.add_argument("--project", default=DEFAULT_PROJECT)
    seed.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    seed.set_defaults(func=command_seed_context)

    export = sub.add_parser("export-expected", help="write the expected challenge graph payload for review/debugging")
    export.add_argument("--output", type=Path, default=Path("sysmlv2-api/challenge-reports/de4sdv-context-expected-graph.json"))
    export.set_defaults(func=command_export_expected)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
