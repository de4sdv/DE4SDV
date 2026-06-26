#!/usr/bin/env python3
"""Small SysON GraphQL/file-exchange helper for the DE4SDV pilot.

This deliberately targets SysON/Sirius Web APIs, not the OMG SysML v2 API
Services endpoints. It is used to prove the SysON side of the engineering
workflow: discover projects, import textual .sysml documents, and download a
SysON document back to a file.
"""

from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any



GRAPHQL_ENDPOINT = "/api/graphql"
GRAPHQL_UPLOAD_ENDPOINT = "/api/graphql/upload"
DOWNLOAD_ENDPOINT = "/api/editingcontexts/{editing_context_id}/documents/{document_id}"
DOWNLOAD_MEDIA_TYPE = "text/html"


def http_requests() -> Any:
    try:
        import requests
    except ModuleNotFoundError as exc:
        raise RuntimeError("SysON exchange commands require the optional 'requests' package") from exc
    return requests

FETCH_PROJECTS_QUERY = """
query FetchProjects {
  viewer {
    projects {
      edges {
        node {
          id
          name
          currentEditingContext {
            id
          }
        }
      }
    }
  }
}
"""

CREATE_PROJECT_MUTATION = """
mutation CreateProject($input: CreateProjectInput!) {
  createProject(input: $input) {
    __typename
    ... on CreateProjectSuccessPayload {
      id
      project {
        id
        name
        currentEditingContext {
          id
        }
      }
    }
    ... on ErrorPayload {
      messages {
        body
        level
      }
    }
  }
}
"""

FETCH_EDITING_CONTEXT_QUERY = """
query FetchEditingContext($projectId: ID!) {
  viewer {
    project(projectId: $projectId) {
      id
      name
      currentEditingContext {
        id
      }
    }
  }
}
"""

UPLOAD_DOCUMENT_MUTATION = """
mutation UploadDocument($input: UploadDocumentInput!) {
  uploadDocument(input: $input) {
    __typename
    ... on UploadDocumentSuccessPayload {
      id
      report
    }
    ... on ErrorPayload {
      messages {
        body
        level
      }
    }
  }
}
"""

SEARCH_QUERY = """
query SearchObjects($editingContextId: ID!, $query: SearchQuery!) {
  viewer {
    editingContext(editingContextId: $editingContextId) {
      search(query: $query) {
        __typename
        ... on SearchSuccessPayload {
          result {
            matches {
              id
              label
              kind
            }
          }
        }
        ... on ErrorPayload {
          messages {
            body
            level
          }
        }
      }
    }
  }
}
"""

LIST_REPRESENTATIONS_QUERY = """
query ListRepresentations($editingContextId: ID!) {
  viewer {
    editingContext(editingContextId: $editingContextId) {
      representations(first: 100) {
        edges {
          node {
            id
            label
            kind
            description {
              id
              label
            }
          }
        }
      }
    }
  }
}
"""

REPRESENTATION_DESCRIPTIONS_QUERY = """
query RepresentationDescriptions($editingContextId: ID!, $objectId: ID!) {
  viewer {
    editingContext(editingContextId: $editingContextId) {
      representationDescriptions(objectId: $objectId) {
        edges {
          node {
            id
            label
          }
        }
      }
    }
  }
}
"""

CREATE_REPRESENTATION_MUTATION = """
mutation CreateRepresentation($input: CreateRepresentationInput!) {
  createRepresentation(input: $input) {
    __typename
    ... on CreateRepresentationSuccessPayload {
      id
      representation {
        id
        label
        kind
        description {
          id
          label
        }
      }
    }
    ... on ErrorPayload {
      messages {
        body
        level
      }
    }
  }
}
"""

INSERT_TEXTUAL_SYSML_MUTATION = """
mutation InsertTextualSysMLv2($input: InsertTextualSysMLv2Input!) {
  insertTextualSysMLv2(input: $input) {
    __typename
    ... on InsertTextualSysMLv2SuccessPayload {
      id
      report {
        id
        entries {
          message
          severity
        }
      }
    }
    ... on ErrorPayload {
      messages {
        body
        level
      }
    }
  }
}
"""


def graphql_url(url: str) -> str:
    return f"{url.rstrip('/')}{GRAPHQL_ENDPOINT}"


def graphql_upload_url(url: str) -> str:
    return f"{url.rstrip('/')}{GRAPHQL_UPLOAD_ENDPOINT}"


def download_url(url: str, editing_context_id: str, document_id: str) -> str:
    return f"{url.rstrip('/')}{DOWNLOAD_ENDPOINT.format(editing_context_id=editing_context_id, document_id=document_id)}"


def post_graphql(url: str, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    requests = http_requests()
    response = requests.post(graphql_url(url), json={"query": query, "variables": variables or {}}, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"GraphQL HTTP {response.status_code}: {response.text[:2000]}")
    data = response.json()
    if data.get("errors"):
        raise RuntimeError("GraphQL errors: " + json.dumps(data["errors"], indent=2))
    return data


SUPPORTED_ELEMENTS = [
    {"semantic_id": "Package:DE4SDV", "type": "Package", "name": "DE4SDV"},
    {"semantic_id": "Package:EngineeringAssets", "type": "Package", "name": "EngineeringAssets"},
    {"semantic_id": "Package:Context", "type": "Package", "name": "Context"},
    {"semantic_id": "Package:RelationshipIntents", "type": "Package", "name": "RelationshipIntents"},
    {"semantic_id": "PartDefinition:ConfigurableSDVProductLine", "type": "PartDefinition", "name": "ConfigurableSDVProductLine"},
    {"semantic_id": "PartDefinition:LifecycleEngineeringSystem", "type": "PartDefinition", "name": "LifecycleEngineeringSystem"},
    {"semantic_id": "PartDefinition:OpenInnovationEcosystem", "type": "PartDefinition", "name": "OpenInnovationEcosystem"},
    {"semantic_id": "PartDefinition:ModelRepository", "type": "PartDefinition", "name": "ModelRepository"},
    {"semantic_id": "PartDefinition:ValidationPipeline", "type": "PartDefinition", "name": "ValidationPipeline"},
    {"semantic_id": "PartDefinition:EvidenceBaseline", "type": "PartDefinition", "name": "EvidenceBaseline"},
    {"semantic_id": "PartUsage:engineeredProductLine", "type": "PartUsage", "name": "engineeredProductLine", "definition": "ConfigurableSDVProductLine", "is_reference": True},
    {"semantic_id": "PartUsage:modelRepository", "type": "PartUsage", "name": "modelRepository", "definition": "ModelRepository", "is_reference": False},
    {"semantic_id": "PartUsage:validationPipeline", "type": "PartUsage", "name": "validationPipeline", "definition": "ValidationPipeline", "is_reference": False},
    {"semantic_id": "PartUsage:evidenceBaseline", "type": "PartUsage", "name": "evidenceBaseline", "definition": "EvidenceBaseline", "is_reference": False},
    {"semantic_id": "PartUsage:governedLifecycleSystem", "type": "PartUsage", "name": "governedLifecycleSystem", "definition": "LifecycleEngineeringSystem", "is_reference": True},
    {"semantic_id": "Dependency:governs / evolves", "type": "Dependency", "name": "governs / evolves", "source": "OpenInnovationEcosystem", "target": "LifecycleEngineeringSystem"},
    {"semantic_id": "Dependency:engineers / assures", "type": "Dependency", "name": "engineers / assures", "source": "LifecycleEngineeringSystem", "target": "ConfigurableSDVProductLine"},
    {"semantic_id": "Dependency:manages model baselines", "type": "Dependency", "name": "manages model baselines", "source": "LifecycleEngineeringSystem", "target": "ModelRepository"},
    {"semantic_id": "Dependency:executes validation", "type": "Dependency", "name": "executes validation", "source": "LifecycleEngineeringSystem", "target": "ValidationPipeline"},
    {"semantic_id": "Dependency:maintains assurance evidence", "type": "Dependency", "name": "maintains assurance evidence", "source": "LifecycleEngineeringSystem", "target": "EvidenceBaseline"},
]


def kind_entity(kind: str) -> str:
    if "entity=" in kind:
        return kind.rsplit("entity=", 1)[-1]
    return kind


def create_project(url: str, name: str, *, template_id: str = "sysmlv2-template", library_ids: list[str] | None = None) -> dict[str, Any]:
    variables = {"input": {"id": str(uuid.uuid4()), "name": name, "templateId": template_id, "libraryIds": library_ids or []}}
    data = post_graphql(url, CREATE_PROJECT_MUTATION, variables)
    payload = data.get("data", {}).get("createProject", {})
    if payload.get("__typename") != "CreateProjectSuccessPayload":
        raise RuntimeError("Create project failed: " + json.dumps(payload, indent=2))
    return payload["project"]


def search_objects(url: str, project_id: str, text: str) -> list[dict[str, Any]]:
    context_id = editing_context(url, project_id)
    variables = {
        "editingContextId": context_id,
        "query": {
            "text": text,
            "matchCase": False,
            "matchWholeWord": True,
            "useRegularExpression": False,
            "searchInAttributes": True,
            "searchInLibraries": False,
        },
    }
    data = post_graphql(url, SEARCH_QUERY, variables)
    payload = data.get("data", {}).get("viewer", {}).get("editingContext", {}).get("search", {})
    if payload.get("__typename") != "SearchSuccessPayload":
        raise RuntimeError("Search failed: " + json.dumps(payload, indent=2))
    return payload.get("result", {}).get("matches", [])


def find_document_id(url: str, project_id: str, document_label: str) -> str | None:
    matches = search_objects(url, project_id, document_label)
    for match in matches:
        if match.get("label") == document_label and not match.get("kind"):
            return str(match.get("id"))
    return None


def list_views(url: str, project_id: str) -> list[dict[str, Any]]:
    context_id = editing_context(url, project_id)
    data = post_graphql(url, LIST_REPRESENTATIONS_QUERY, {"editingContextId": context_id})
    edges = data.get("data", {}).get("viewer", {}).get("editingContext", {}).get("representations", {}).get("edges", [])
    return [{**edge["node"], "editingContextId": context_id} for edge in edges]


def representation_descriptions(url: str, project_id: str, object_id: str) -> list[dict[str, Any]]:
    context_id = editing_context(url, project_id)
    data = post_graphql(url, REPRESENTATION_DESCRIPTIONS_QUERY, {"editingContextId": context_id, "objectId": object_id})
    edges = data.get("data", {}).get("viewer", {}).get("editingContext", {}).get("representationDescriptions", {}).get("edges", [])
    return [edge["node"] for edge in edges]


def create_representation(url: str, project_id: str, object_id: str, description_id: str, name: str) -> dict[str, Any]:
    context_id = editing_context(url, project_id)
    variables = {
        "input": {
            "id": str(uuid.uuid4()),
            "editingContextId": context_id,
            "objectId": object_id,
            "representationDescriptionId": description_id,
            "representationName": name,
        }
    }
    data = post_graphql(url, CREATE_REPRESENTATION_MUTATION, variables)
    payload = data.get("data", {}).get("createRepresentation", {})
    if payload.get("__typename") != "CreateRepresentationSuccessPayload":
        raise RuntimeError("Create representation failed: " + json.dumps(payload, indent=2))
    return {**payload["representation"], "editingContextId": context_id}


def psql_representation_content(
    editing_context_id: str,
    representation_id: str,
    *,
    container: str,
    user: str,
    database: str,
) -> dict[str, Any]:
    row_id = f"{editing_context_id}#{representation_id}"
    safe_row_id = row_id.replace("'", "''")
    sql = f"select content from representation_content where id = '{safe_row_id}'"
    command = ["docker", "exec", "-i", container, "psql", "-U", user, "-d", database, "-t", "-A", "-c", sql]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"psql representation export failed: {result.stderr.strip()}")
    content = result.stdout.strip()
    if not content:
        raise RuntimeError(f"representation content not found in SysON database for {row_id}")
    return json.loads(content)


def _walk_nodes(nodes: list[dict[str, Any]], level: int = 0) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for node in nodes:
        flattened.append({**node, "_level": level})
        flattened.extend(_walk_nodes(node.get("childNodes", []) + node.get("borderNodes", []), level + 1))
    return flattened


def _label(value: dict[str, Any]) -> str:
    inside = value.get("insideLabel") or {}
    if inside.get("text"):
        return str(inside["text"])
    labels = value.get("outsideLabels") or []
    if labels and labels[0].get("text"):
        return str(labels[0]["text"])
    if value.get("centerLabel", {}).get("text"):
        return str(value["centerLabel"]["text"])
    return str(value.get("targetObjectId") or value.get("id") or "")


def render_view_svg(view: dict[str, Any]) -> str:
    nodes = _walk_nodes(view.get("nodes", []))
    layout = view.get("layoutData", {})
    layout_by_id = {item.get("id"): item for item in (layout.get("nodeLayoutData") or {}).values()} if isinstance(layout.get("nodeLayoutData"), dict) else {}
    width = max(900, 220 + 220 * max(1, len(nodes)))
    height = max(260, 140 + 90 * max(1, len(nodes)))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>text{font-family:Inter,Arial,sans-serif}.title{font-size:22px;font-weight:700}.meta{font-size:12px;fill:#667}.box{fill:#f8fbff;stroke:#446;stroke-width:1.5}.empty{fill:#fff7e6;stroke:#a66}</style>',
        f'<text class="title" x="24" y="36">{html.escape(str(view.get("label") or view.get("id") or "SysON view"))}</text>',
        f'<text class="meta" x="24" y="58">SysON representation {html.escape(str(view.get("id", "")))}</text>',
    ]
    if not nodes:
        parts.extend([
            '<rect class="empty" x="24" y="90" width="620" height="90" rx="10"/>',
            '<text x="44" y="126" font-size="16">No diagram nodes are currently visible in this SysON view.</text>',
            '<text x="44" y="152" class="meta">Open the view in SysON, add/reveal elements, then re-run export-view.</text>',
        ])
    else:
        node_pos: dict[str, tuple[float, float, float, float]] = {}
        for index, node in enumerate(nodes):
            node_id = node.get("id")
            layout_item = layout_by_id.get(node_id, {})
            position = layout_item.get("position", {})
            size = layout_item.get("size", {})
            x = float(position.get("x", 40 + (index % 4) * 220))
            y = float(position.get("y", 90 + (index // 4) * 110))
            w = float(size.get("width", node.get("defaultWidth") or 180))
            h = float(size.get("height", node.get("defaultHeight") or 70))
            node_pos[str(node_id)] = (x, y, w, h)
            parts.append(f'<rect class="box" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="8"/>')
            parts.append(f'<text x="{x + 12:.1f}" y="{y + 28:.1f}" font-size="14">{html.escape(_label(node))}</text>')
            parts.append(f'<text class="meta" x="{x + 12:.1f}" y="{y + h - 12:.1f}">{html.escape(str(node.get("type", "")))}</text>')
        for edge in view.get("edges", []):
            source = node_pos.get(str(edge.get("sourceId")))
            target = node_pos.get(str(edge.get("targetId")))
            if not source or not target:
                continue
            sx, sy, sw, sh = source
            tx, ty, tw, th = target
            x1, y1 = sx + sw, sy + sh / 2
            x2, y2 = tx, ty + th / 2
            parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#668" stroke-width="1.5" marker-end="url(#arrow)"/>')
            label = _label(edge)
            if label:
                parts.append(f'<text class="meta" x="{(x1+x2)/2:.1f}" y="{(y1+y2)/2 - 6:.1f}">{html.escape(label)}</text>')
    parts.insert(2, '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#668"/></marker></defs>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def export_view_artifacts(view: dict[str, Any], output_dir: Path, stem: str) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{stem}.view.json"
    svg_path = output_dir / f"{stem}.svg"
    manifest_path = output_dir / f"{stem}.manifest.json"
    json_path.write_text(json.dumps(view, indent=2) + "\n")
    svg_path.write_text(render_view_svg(view))
    manifest = {
        "schema": "de4sdv.syson-view-publication.v1",
        "representation_id": view.get("id"),
        "target_object_id": view.get("targetObjectId"),
        "label": view.get("label"),
        "artifacts": {"json": str(json_path), "svg": str(svg_path)},
        "note": "Tool-specific SysON/Sirius diagram publication artifact; not native SysML v2 API view evidence.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return {"json": str(json_path), "svg": str(svg_path), "manifest": str(manifest_path)}


def export_supported_graph(url: str, project_id: str) -> dict[str, Any]:
    """Export the DE4SDV supported subset from SysON search evidence."""
    exported: list[dict[str, Any]] = []
    missing: list[dict[str, str]] = []
    for expected in SUPPORTED_ELEMENTS:
        matches = search_objects(url, project_id, expected["name"])
        expected_type = expected["type"]
        typed_matches = [m for m in matches if kind_entity(m.get("kind", "")) == expected_type and m.get("label") == expected["name"]]
        if not typed_matches:
            missing.append({"semantic_id": expected["semantic_id"], "type": expected_type, "name": expected["name"]})
            continue
        match = typed_matches[0]
        exported.append({**expected, "syson": {"id": match.get("id", ""), "kind": match.get("kind", ""), "label": match.get("label", "")}})
    status = "failed" if missing else "passed-with-warnings"
    return {
        "schema": "de4sdv.syson-supported-graph.v1",
        "source": "SysON GraphQL search plus DE4SDV supported-subset canonical relationships",
        "project_id": project_id,
        "editing_context_id": editing_context(url, project_id),
        "summary": {"status": status, "exported": len(exported), "missing": len(missing)},
        "elements": exported,
        "missing": missing,
        "warnings": [
            "SysON v2026.5.0 native textual export drops dependency declarations for this slice.",
            "SysON GraphQL search confirms dependency objects exist, but dependency endpoints are not exposed through queryBasedObjects for source/target/client/supplier.",
            "This supported graph adapter validates SysON object presence and carries canonical DE4SDV supported-subset dependency endpoints for API re-import.",
        ],
    }


def list_projects(url: str) -> list[dict[str, Any]]:
    data = post_graphql(url, FETCH_PROJECTS_QUERY)
    edges = data.get("data", {}).get("viewer", {}).get("projects", {}).get("edges", [])
    return [edge["node"] for edge in edges]


def editing_context(url: str, project_id: str) -> str:
    data = post_graphql(url, FETCH_EDITING_CONTEXT_QUERY, {"projectId": project_id})
    project = data.get("data", {}).get("viewer", {}).get("project")
    if not project:
        raise RuntimeError(f"Project not found: {project_id}")
    context = project.get("currentEditingContext")
    if not context:
        raise RuntimeError(f"Editing context not found for project: {project_id}")
    return context["id"]


def import_document(url: str, project_id: str, file_path: Path, *, read_only: bool) -> dict[str, Any]:
    if file_path.suffix != ".sysml":
        raise RuntimeError("SysON textual import expects a .sysml file")
    context_id = editing_context(url, project_id)
    operation_id = str(uuid.uuid4())
    operations = {
        "query": UPLOAD_DOCUMENT_MUTATION,
        "variables": {
            "input": {
                "id": operation_id,
                "editingContextId": context_id,
                "file": None,
                "readOnly": read_only,
            }
        },
    }
    file_map = {"0": "variables.file"}
    requests = http_requests()
    with file_path.open("rb") as handle:
        response = requests.post(
            graphql_upload_url(url),
            data={"operations": json.dumps(operations), "map": json.dumps(file_map)},
            files={"0": (file_path.name, handle, "text/plain")},
            timeout=120,
        )
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Upload HTTP {response.status_code}: {response.text[:2000]}")
    data = response.json()
    if data.get("errors"):
        raise RuntimeError("GraphQL errors: " + json.dumps(data["errors"], indent=2))
    return data


def insert_text(url: str, project_id: str, object_id: str, file_path: Path) -> dict[str, Any]:
    context_id = editing_context(url, project_id)
    text = file_path.read_text()
    variables = {
        "input": {
            "id": str(uuid.uuid4()),
            "editingContextId": context_id,
            "objectId": object_id,
            "textualContent": text,
        }
    }
    return post_graphql(url, INSERT_TEXTUAL_SYSML_MUTATION, variables)


def download_document(url: str, project_id: str, document_id: str, output_path: Path) -> None:
    context_id = editing_context(url, project_id)
    requests = http_requests()
    response = requests.get(download_url(url, context_id, document_id), headers={"Accept": DOWNLOAD_MEDIA_TYPE}, timeout=180)
    if response.status_code != 200:
        raise RuntimeError(f"Download HTTP {response.status_code}: {response.text[:2000]}")
    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type:
        raise RuntimeError(f"Unexpected download content type {content_type!r}; SysON v2026.5.0 exporter is registered for {DOWNLOAD_MEDIA_TYPE}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8080", help="SysON base URL")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-projects")

    create_parser = sub.add_parser("create-project")
    create_parser.add_argument("name")
    create_parser.add_argument("--template-id", default="sysmlv2-template")

    list_views_parser = sub.add_parser("list-views")
    list_views_parser.add_argument("project_id")

    describe_view_parser = sub.add_parser("representation-descriptions")
    describe_view_parser.add_argument("project_id")
    describe_view_parser.add_argument("object_id")

    create_view_parser = sub.add_parser("create-view")
    create_view_parser.add_argument("project_id")
    create_view_parser.add_argument("object_id")
    create_view_parser.add_argument("description_id")
    create_view_parser.add_argument("name")

    export_view_parser = sub.add_parser("export-view")
    export_view_parser.add_argument("project_id")
    export_view_parser.add_argument("representation_id")
    export_view_parser.add_argument("output_dir", type=Path)
    export_view_parser.add_argument("--stem", default="syson-view")
    export_view_parser.add_argument("--postgres-container", default="syson-database-1")
    export_view_parser.add_argument("--postgres-user", default="username")
    export_view_parser.add_argument("--postgres-db", default="postgres")

    export_graph_parser = sub.add_parser("export-supported-graph")
    export_graph_parser.add_argument("project_id")
    export_graph_parser.add_argument("output", type=Path)

    import_parser = sub.add_parser("import-document")
    import_parser.add_argument("project_id")
    import_parser.add_argument("file", type=Path)
    import_parser.add_argument("--read-only", action="store_true")

    insert_parser = sub.add_parser("insert-text")
    insert_parser.add_argument("project_id")
    insert_parser.add_argument("object_id")
    insert_parser.add_argument("file", type=Path)

    download_parser = sub.add_parser("download-document")
    download_parser.add_argument("project_id")
    download_parser.add_argument("document_id")
    download_parser.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "list-projects":
        print(json.dumps(list_projects(args.url), indent=2))
    elif args.command == "create-project":
        print(json.dumps(create_project(args.url, args.name, template_id=args.template_id), indent=2))
    elif args.command == "list-views":
        print(json.dumps(list_views(args.url, args.project_id), indent=2))
    elif args.command == "representation-descriptions":
        print(json.dumps(representation_descriptions(args.url, args.project_id, args.object_id), indent=2))
    elif args.command == "create-view":
        print(json.dumps(create_representation(args.url, args.project_id, args.object_id, args.description_id, args.name), indent=2))
    elif args.command == "export-view":
        context_id = editing_context(args.url, args.project_id)
        view = psql_representation_content(
            context_id,
            args.representation_id,
            container=args.postgres_container,
            user=args.postgres_user,
            database=args.postgres_db,
        )
        for metadata in list_views(args.url, args.project_id):
            if metadata.get("id") == args.representation_id:
                view.setdefault("label", metadata.get("label"))
                view.setdefault("metadata", metadata)
                break
        artifacts = export_view_artifacts(view, args.output_dir, args.stem)
        print(json.dumps(artifacts, indent=2))
    elif args.command == "export-supported-graph":
        graph = export_supported_graph(args.url, args.project_id)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(graph, indent=2) + "\n")
        print(f"wrote supported graph: {args.output}")
        if graph["summary"]["status"] == "failed":
            return 2
    elif args.command == "import-document":
        print(json.dumps(import_document(args.url, args.project_id, args.file, read_only=args.read_only), indent=2))
    elif args.command == "insert-text":
        print(json.dumps(insert_text(args.url, args.project_id, args.object_id, args.file), indent=2))
    elif args.command == "download-document":
        download_document(args.url, args.project_id, args.document_id, args.output)
        print(f"downloaded: {args.output}")
    else:
        parser.error(f"unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
