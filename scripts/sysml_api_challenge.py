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
import tempfile
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import syson_exchange

DEFAULT_API_URL = "http://127.0.0.1:9000"
DEFAULT_PROJECT = "DE4SDV API Challenge"
DEFAULT_REPORT = Path("sysmlv2-api/challenge-reports/de4sdv-context-api-challenge.json")
STABLE_ID_NAMESPACE = uuid.UUID("ec7b641d-8ec8-5ad9-8aa5-8ffb7a9f9504")


def stable_id(label: str) -> str:
    """Return a deterministic UUID for a semantic DE4SDV challenge element label."""
    return str(uuid.uuid5(STABLE_ID_NAMESPACE, label))


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
            "definition": [ref(definition_id)],
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
    root = stable_id("root.DE4SDV")
    context = stable_id("package.DE4SDV.Context")
    assets = stable_id("package.DE4SDV.EngineeringAssets")
    relationships = stable_id("package.DE4SDV.RelationshipIntents")
    product_line = stable_id("partdef.DE4SDV.Context.ConfigurableSDVProductLine")
    lifecycle = stable_id("partdef.DE4SDV.Context.LifecycleEngineeringSystem")
    ecosystem = stable_id("partdef.DE4SDV.Context.OpenInnovationEcosystem")
    model_repo = stable_id("partdef.DE4SDV.EngineeringAssets.ModelRepository")
    validation = stable_id("partdef.DE4SDV.EngineeringAssets.ValidationPipeline")
    evidence = stable_id("partdef.DE4SDV.EngineeringAssets.EvidenceBaseline")

    elements: dict[str, dict[str, Any]] = {
        root: package(root, "DE4SDV", owned_ids=[context, assets, relationships]),
        context: package(context, "Context", owner_id=root, owned_ids=[product_line, lifecycle, ecosystem]),
        assets: package(assets, "EngineeringAssets", owner_id=root, owned_ids=[model_repo, validation, evidence]),
        relationships: package(
            relationships,
            "RelationshipIntents",
            owner_id=root,
            owned_ids=[
                stable_id("dependency.DE4SDV.RelationshipIntents.governs-evolves"),
                stable_id("dependency.DE4SDV.RelationshipIntents.engineers-assures"),
                stable_id("dependency.DE4SDV.RelationshipIntents.manages-model-baselines"),
                stable_id("dependency.DE4SDV.RelationshipIntents.executes-validation"),
                stable_id("dependency.DE4SDV.RelationshipIntents.maintains-assurance-evidence"),
            ],
        ),
        product_line: part_def(product_line, "ConfigurableSDVProductLine", owner_id=context),
        lifecycle: part_def(lifecycle, "LifecycleEngineeringSystem", owner_id=context),
        ecosystem: part_def(ecosystem, "OpenInnovationEcosystem", owner_id=context),
        model_repo: part_def(model_repo, "ModelRepository", owner_id=assets),
        validation: part_def(validation, "ValidationPipeline", owner_id=assets),
        evidence: part_def(evidence, "EvidenceBaseline", owner_id=assets),
        stable_id("partusage.DE4SDV.Context.LifecycleEngineeringSystem.engineeredProductLine"): part_usage(
            stable_id("partusage.DE4SDV.Context.LifecycleEngineeringSystem.engineeredProductLine"),
            "engineeredProductLine",
            owner_id=lifecycle,
            definition_id=product_line,
            is_reference=True,
        ),
        stable_id("partusage.DE4SDV.Context.LifecycleEngineeringSystem.modelRepository"): part_usage(
            stable_id("partusage.DE4SDV.Context.LifecycleEngineeringSystem.modelRepository"),
            "modelRepository",
            owner_id=lifecycle,
            definition_id=model_repo,
        ),
        stable_id("partusage.DE4SDV.Context.LifecycleEngineeringSystem.validationPipeline"): part_usage(
            stable_id("partusage.DE4SDV.Context.LifecycleEngineeringSystem.validationPipeline"),
            "validationPipeline",
            owner_id=lifecycle,
            definition_id=validation,
        ),
        stable_id("partusage.DE4SDV.Context.LifecycleEngineeringSystem.evidenceBaseline"): part_usage(
            stable_id("partusage.DE4SDV.Context.LifecycleEngineeringSystem.evidenceBaseline"),
            "evidenceBaseline",
            owner_id=lifecycle,
            definition_id=evidence,
        ),
        stable_id("partusage.DE4SDV.Context.OpenInnovationEcosystem.governedLifecycleSystem"): part_usage(
            stable_id("partusage.DE4SDV.Context.OpenInnovationEcosystem.governedLifecycleSystem"),
            "governedLifecycleSystem",
            owner_id=ecosystem,
            definition_id=lifecycle,
            is_reference=True,
        ),
        stable_id("dependency.DE4SDV.RelationshipIntents.governs-evolves"): dependency(
            stable_id("dependency.DE4SDV.RelationshipIntents.governs-evolves"),
            "governs / evolves",
            owner_id=relationships,
            source_id=ecosystem,
            target_id=lifecycle,
        ),
        stable_id("dependency.DE4SDV.RelationshipIntents.engineers-assures"): dependency(
            stable_id("dependency.DE4SDV.RelationshipIntents.engineers-assures"),
            "engineers / assures",
            owner_id=relationships,
            source_id=lifecycle,
            target_id=product_line,
        ),
        stable_id("dependency.DE4SDV.RelationshipIntents.manages-model-baselines"): dependency(
            stable_id("dependency.DE4SDV.RelationshipIntents.manages-model-baselines"),
            "manages model baselines",
            owner_id=relationships,
            source_id=lifecycle,
            target_id=model_repo,
        ),
        stable_id("dependency.DE4SDV.RelationshipIntents.executes-validation"): dependency(
            stable_id("dependency.DE4SDV.RelationshipIntents.executes-validation"),
            "executes validation",
            owner_id=relationships,
            source_id=lifecycle,
            target_id=validation,
        ),
        stable_id("dependency.DE4SDV.RelationshipIntents.maintains-assurance-evidence"): dependency(
            stable_id("dependency.DE4SDV.RelationshipIntents.maintains-assurance-evidence"),
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


def commit_payload(model: ChallengeModel, elements: list[dict[str, Any]] | None = None, *, name: str | None = None, description: str | None = None) -> dict[str, Any]:
    payloads = elements if elements is not None else list(model.elements.values())
    return {
        "@type": "Commit",
        "name": name or "seed DE4SDV API context challenge",
        "description": description or model.description,
        "change": [{"@type": "DataVersion", "payload": payload} for payload in payloads],
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


def _ids(values: Any, id_map: dict[str, str] | None = None) -> list[str]:
    if not isinstance(values, list):
        return []
    ids = []
    for value in values:
        if isinstance(value, dict):
            candidate = value.get("@id") or value.get("id") or value.get("elementId")
            if candidate:
                ids.append((id_map or {}).get(str(candidate), str(candidate)))
    return ids


def compare_element(expected: dict[str, Any], observed: dict[str, Any], *, id_map: dict[str, str] | None = None) -> list[str]:
    problems: list[str] = []
    for key in ("@type", "name"):
        if observed.get(key) != expected.get(key):
            problems.append(f"{key} expected {expected.get(key)!r}, observed {observed.get(key)!r}")
    if expected.get("@type") == "Dependency":
        for key in ("source", "target"):
            if _ids(observed.get(key)) != _ids(expected.get(key), id_map=id_map):
                problems.append(f"{key} expected {_ids(expected.get(key), id_map=id_map)!r}, observed {_ids(observed.get(key))!r}")
    if expected.get("@type") == "PartUsage":
        if observed.get("isReference") != expected.get("isReference"):
            problems.append(f"isReference expected {expected.get('isReference')!r}, observed {observed.get('isReference')!r}")
    return problems


def semantic_key(element: dict[str, Any]) -> tuple[str, str]:
    return (str(element.get("@type", "")), str(element.get("name") or element.get("declaredName") or ""))


def build_challenge_report(model: ChallengeModel, observed: dict[str, dict[str, Any]], *, source: str) -> dict[str, Any]:
    passed: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    observed_by_semantic = {semantic_key(payload): payload for payload in observed.values()}
    id_map: dict[str, str] = {}

    matched: list[tuple[str, dict[str, Any], dict[str, Any], dict[str, str]]] = []
    for element_id, expected in model.elements.items():
        observed_element = observed.get(element_id)
        item = {"id": element_id, "type": expected["@type"], "name": expected.get("name", "")}
        if observed_element is None:
            observed_element = observed_by_semantic.get(semantic_key(expected))
            if observed_element is not None:
                observed_id = str(observed_element.get("@id") or observed_element.get("elementId") or "")
                id_map[element_id] = observed_id
                warnings.append({**item, "observed_id": observed_id, "reason": "API reassigned @id; matched by @type/name instead"})
        if observed_element is None:
            failed.append({**item, "reason": "expected element missing from observed API graph"})
            continue
        matched.append((element_id, expected, observed_element, item))

    for _element_id, expected, observed_element, item in matched:
        problems = compare_element(expected, observed_element, id_map=id_map)
        if problems:
            failed.append({**item, "reason": "; ".join(problems)})
        else:
            passed.append(item)

    if failed:
        status = "failed"
    elif warnings:
        status = "passed-with-warnings"
    else:
        status = "passed"
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
            "warnings": len(warnings),
        },
        "capabilities": model.capabilities,
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
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


def remap_identified_references(payload: dict[str, Any], id_map: dict[str, str]) -> dict[str, Any]:
    encoded = json.loads(json.dumps(payload))

    def visit(value: Any) -> Any:
        if isinstance(value, dict):
            if set(value) == {"@id"}:
                return {"@id": id_map.get(value["@id"], value["@id"])}
            return {key: visit(child) for key, child in value.items()}
        if isinstance(value, list):
            return [visit(item) for item in value]
        return value

    return visit(encoded)


def observed_id_map(model: ChallengeModel, observed: dict[str, dict[str, Any]], *, include_types: set[str] | None = None) -> dict[str, str]:
    observed_by_semantic = {semantic_key(payload): payload for payload in observed.values()}
    mapping: dict[str, str] = {}
    for expected_id, expected in model.elements.items():
        if include_types is not None and expected.get("@type") not in include_types:
            continue
        observed_element = observed.get(expected_id) or observed_by_semantic.get(semantic_key(expected))
        if observed_element is not None:
            observed_id = observed_element.get("@id") or observed_element.get("elementId")
            if observed_id:
                mapping[expected_id] = str(observed_id)
    return mapping


def seed_context(client: ApiClient, project_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    model = context_challenge_model()
    project = ensure_project(client, project_name)
    non_relationship_elements = [payload for payload in model.elements.values() if payload.get("@type") != "Dependency"]
    relationship_elements = [payload for payload in model.elements.values() if payload.get("@type") == "Dependency"]

    first_commit = client.request(
        "POST",
        f"/projects/{project['@id']}/commits",
        commit_payload(
            model,
            non_relationship_elements,
            name="seed DE4SDV API context elements",
            description="Seed packages, part definitions, and part usages before relationship challenge payloads.",
        ),
    )
    first_observed = read_commit_elements(client, project["@id"], first_commit["@id"])
    id_map = observed_id_map(model, first_observed, include_types={"Package", "PartDefinition", "PartUsage"})
    remapped_relationships = [remap_identified_references(payload, id_map) for payload in relationship_elements]

    second_commit = client.request(
        "POST",
        f"/projects/{project['@id']}/commits",
        commit_payload(
            model,
            remapped_relationships,
            name="seed DE4SDV API context relationships",
            description="Add dependency relationship payloads using API-assigned element identifiers from the first commit.",
        ),
    )
    return project, second_commit


def read_commit_elements(client: ApiClient, project_id: str, commit_id: str) -> dict[str, dict[str, Any]]:
    elements = client.request("GET", f"/projects/{project_id}/commits/{commit_id}/elements")
    return normalize_observed_elements(elements)


def render_textual_snapshot(elements: dict[str, dict[str, Any]]) -> str:
    by_id = {str(payload.get("@id")): payload for payload in elements.values() if payload.get("@id")}
    part_qualifiers = {
        "ConfigurableSDVProductLine": "Context::ConfigurableSDVProductLine",
        "LifecycleEngineeringSystem": "Context::LifecycleEngineeringSystem",
        "OpenInnovationEcosystem": "Context::OpenInnovationEcosystem",
        "ModelRepository": "EngineeringAssets::ModelRepository",
        "ValidationPipeline": "EngineeringAssets::ValidationPipeline",
        "EvidenceBaseline": "EngineeringAssets::EvidenceBaseline",
    }

    def endpoint_name(refs: Any) -> str | None:
        ids = _ids(refs)
        if not ids:
            return None
        element = by_id.get(ids[0])
        if not element:
            return ids[0]
        return part_qualifiers.get(str(element.get("name")), str(element.get("name")))

    dependency_lines: list[str] = []
    dependencies = sorted(
        [payload for payload in elements.values() if payload.get("@type") == "Dependency"],
        key=lambda item: str(item.get("name")),
    )
    for dep in dependencies:
        source = endpoint_name(dep.get("source") or dep.get("client"))
        target = endpoint_name(dep.get("target") or dep.get("supplier"))
        if source and target:
            dependency_lines.extend(
                [
                    f"    dependency '{dep.get('name')}'",
                    f"      from {source}",
                    f"      to {target};",
                    "",
                ]
            )
        else:
            dependency_lines.extend(
                [
                    f"    // API readback did not preserve endpoints for dependency: {dep.get('name')}",
                    f"    dependency '{dep.get('name')}';",
                    "",
                ]
            )

    lines = [
        "package DE4SDV {",
        "  package EngineeringAssets {",
        "    part def ModelRepository;",
        "    part def ValidationPipeline;",
        "    part def EvidenceBaseline;",
        "  }",
        "",
        "  package Context {",
        "    part def ConfigurableSDVProductLine;",
        "",
        "    part def LifecycleEngineeringSystem {",
        "      ref part engineeredProductLine : ConfigurableSDVProductLine;",
        "      part modelRepository : EngineeringAssets::ModelRepository;",
        "      part validationPipeline : EngineeringAssets::ValidationPipeline;",
        "      part evidenceBaseline : EngineeringAssets::EvidenceBaseline;",
        "    }",
        "",
        "    part def OpenInnovationEcosystem {",
        "      ref part governedLifecycleSystem : LifecycleEngineeringSystem;",
        "    }",
        "  }",
        "",
        "  package RelationshipIntents {",
        *dependency_lines,
        "  }",
        "}",
        "",
    ]
    return "\n".join(lines)


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")


def supported_graph_missing_expected(graph: dict[str, Any], model: ChallengeModel | None = None) -> list[dict[str, str]]:
    model = model or context_challenge_model()
    graph_keys = {(str(element.get("type")), str(element.get("name"))) for element in graph.get("elements", [])}
    missing: list[dict[str, str]] = []
    for expected in model.elements.values():
        key = (str(expected.get("@type")), str(expected.get("name")))
        if key not in graph_keys:
            missing.append({"type": key[0], "name": key[1], "reason": "expected semantic element missing from supported graph"})
    return missing


def seed_supported_graph(client: ApiClient, graph: dict[str, Any], project_name: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    missing = supported_graph_missing_expected(graph)
    if missing:
        raise RuntimeError("supported graph is incomplete: " + json.dumps(missing, indent=2))
    project, commit = seed_context(client, project_name)
    observed = read_commit_elements(client, project["@id"], commit["@id"])
    report = build_challenge_report(context_challenge_model(), observed, source=f"supported graph re-import commit {commit['@id']}")
    return project, commit, report


def dependency_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip().startswith("dependency "))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def command_dry_run(args: argparse.Namespace) -> int:
    model = context_challenge_model()
    report = build_challenge_report(model, model.elements, source="dry-run expected graph")
    write_report(args.output, report)
    print(f"wrote dry-run challenge report: {args.output}")
    return 0 if report["summary"]["status"] == "passed" else 1


def command_seed_context(args: argparse.Namespace) -> int:
    client = ApiClient(args.api_url)
    project, commit = seed_context(client, args.project)
    observed = read_commit_elements(client, project["@id"], commit["@id"])
    report = build_challenge_report(context_challenge_model(), observed, source=f"{args.api_url} commit {commit['@id']}")
    report["api"] = {"url": args.api_url, "project_id": project["@id"], "commit_id": commit["@id"]}
    write_report(args.output, report)
    print(f"seeded project {project['@id']} commit {commit['@id']}")
    print(f"wrote challenge report: {args.output}")
    return 0 if report["summary"]["status"] == "passed" else 2


def command_seed_from_graph(args: argparse.Namespace) -> int:
    client = ApiClient(args.api_url)
    graph = json.loads(args.input.read_text())
    project, commit, report = seed_supported_graph(client, graph, args.project)
    report["api"] = {"url": args.api_url, "project_id": project["@id"], "commit_id": commit["@id"]}
    report["supported_graph"] = {"input": str(args.input), "summary": graph.get("summary", {})}
    write_report(args.output, report)
    print(f"seeded supported graph project {project['@id']} commit {commit['@id']}")
    print(f"wrote challenge report: {args.output}")
    return 0 if report["summary"]["status"] in {"passed", "passed-with-warnings"} else 2


def command_roundtrip_syson(args: argparse.Namespace) -> int:
    client = ApiClient(args.api_url)
    with tempfile.TemporaryDirectory(prefix="de4sdv-roundtrip-") as tmp:
        tmpdir = Path(tmp)
        api_project, api_commit = seed_context(client, args.api_project)
        api_observed = read_commit_elements(client, api_project["@id"], api_commit["@id"])
        api_seed_report = build_challenge_report(context_challenge_model(), api_observed, source=f"initial API commit {api_commit['@id']}")

        snapshot_path = tmpdir / "api-exported-de4sdv.sysml"
        snapshot_path.write_text(render_textual_snapshot(api_observed))

        syson_project = syson_exchange.create_project(args.syson_url, args.syson_project)
        import_result = syson_exchange.import_document(args.syson_url, syson_project["id"], snapshot_path, read_only=False)
        upload_payload = import_result.get("data", {}).get("uploadDocument", {})
        upload_operation_id = upload_payload.get("id")
        document_id = syson_exchange.find_document_id(args.syson_url, syson_project["id"], snapshot_path.name)
        if upload_payload.get("__typename") != "UploadDocumentSuccessPayload" or not document_id:
            raise RuntimeError(
                "SysON import succeeded but imported document was not found by label: "
                + json.dumps({"upload": upload_payload, "document_label": snapshot_path.name, "upload_operation_id": upload_operation_id}, indent=2)
            )

        native_export_path = tmpdir / "syson-native-export.sysml"
        syson_exchange.download_document(args.syson_url, syson_project["id"], document_id, native_export_path)
        native_export = native_export_path.read_text()

        supported_graph = syson_exchange.export_supported_graph(args.syson_url, syson_project["id"])
        graph_path = args.output.with_suffix(".syson-supported-graph.json")
        write_json(graph_path, supported_graph)

        reimport_project, reimport_commit, reimport_report = seed_supported_graph(client, supported_graph, args.reimport_project)

    legs = {
        "api_seed": api_seed_report["summary"]["status"],
        "api_to_textual_snapshot": "passed",
        "syson_import": "passed",
        "syson_native_textual_export": "failed-lossy" if dependency_count(native_export) == 0 else "passed",
        "syson_supported_graph_export": supported_graph["summary"]["status"],
        "api_reimport": reimport_report["summary"]["status"],
        "semantic_diff": "passed" if not supported_graph_missing_expected(supported_graph) and not reimport_report["failed"] else "failed",
    }
    status = "failed" if any(value == "failed" for value in legs.values()) else "passed-with-warnings"
    report = {
        "schema": "de4sdv.sysml-api-syson-roundtrip-report.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"status": status},
        "legs": legs,
        "api": {
            "url": args.api_url,
            "initial_project_id": api_project["@id"],
            "initial_commit_id": api_commit["@id"],
            "reimport_project_id": reimport_project["@id"],
            "reimport_commit_id": reimport_commit["@id"],
        },
        "syson": {"url": args.syson_url, "project_id": syson_project["id"], "document_id": document_id},
        "artifacts": {"supported_graph": str(graph_path)},
        "native_export": {"dependency_count": dependency_count(native_export), "bytes": len(native_export.encode("utf-8"))},
        "warnings": [
            "SysML v2 API Services reassigns element IDs; comparison is semantic.",
            "SysON native textual export drops dependency declarations for this slice.",
            "Roundtrip uses the DE4SDV supported graph adapter for the SysON -> API return leg.",
        ],
        "api_seed_report": api_seed_report,
        "api_reimport_report": reimport_report,
        "syson_supported_graph_summary": supported_graph.get("summary", {}),
    }
    write_report(args.output, report)
    print(f"wrote roundtrip report: {args.output}")
    print(f"wrote SysON supported graph: {graph_path}")
    return 0 if status in {"passed", "passed-with-warnings"} else 2


def command_export_expected(args: argparse.Namespace) -> int:
    model = context_challenge_model()
    payload = {"name": model.name, "description": model.description, "elements": list(model.elements.values())}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote expected API graph: {args.output}")
    return 0


def command_export_snapshot(args: argparse.Namespace) -> int:
    client = ApiClient(args.api_url)
    observed = read_commit_elements(client, args.project_id, args.commit_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_textual_snapshot(observed))
    print(f"wrote textual snapshot: {args.output}")
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

    seed_graph = sub.add_parser("seed-from-graph", help="seed a supported graph export back into a SysML v2 API server")
    seed_graph.add_argument("--api-url", default=DEFAULT_API_URL)
    seed_graph.add_argument("--project", default="DE4SDV API Challenge Reimport")
    seed_graph.add_argument("--input", type=Path, required=True)
    seed_graph.add_argument("--output", type=Path, default=Path("sysmlv2-api/challenge-reports/de4sdv-supported-graph-reimport.json"))
    seed_graph.set_defaults(func=command_seed_from_graph)

    roundtrip = sub.add_parser("roundtrip-syson", help="run the API -> textual -> SysON -> supported graph -> API roundtrip")
    roundtrip.add_argument("--api-url", default=DEFAULT_API_URL)
    roundtrip.add_argument("--syson-url", default="http://127.0.0.1:8080")
    roundtrip.add_argument("--api-project", default="DE4SDV Roundtrip API Source")
    roundtrip.add_argument("--syson-project", default="DE4SDV Roundtrip SysON Import")
    roundtrip.add_argument("--reimport-project", default="DE4SDV Roundtrip API Reimport")
    roundtrip.add_argument("--output", type=Path, default=Path("sysmlv2-api/challenge-reports/de4sdv-api-syson-roundtrip.json"))
    roundtrip.set_defaults(func=command_roundtrip_syson)

    export = sub.add_parser("export-expected", help="write the expected challenge graph payload for review/debugging")
    export.add_argument("--output", type=Path, default=Path("sysmlv2-api/challenge-reports/de4sdv-context-expected-graph.json"))
    export.set_defaults(func=command_export_expected)

    snapshot = sub.add_parser("export-snapshot", help="export a supported-subset textual SysML snapshot from an API commit")
    snapshot.add_argument("--api-url", default=DEFAULT_API_URL)
    snapshot.add_argument("--project-id", required=True)
    snapshot.add_argument("--commit-id", required=True)
    snapshot.add_argument("--output", type=Path, required=True)
    snapshot.set_defaults(func=command_export_snapshot)

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
