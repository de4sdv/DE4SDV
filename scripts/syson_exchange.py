#!/usr/bin/env python3
"""Small SysON GraphQL/file-exchange helper for the DE4SDV pilot.

This deliberately targets SysON/Sirius Web APIs, not the OMG SysML v2 API
Services endpoints. It is used to prove the SysON side of the engineering
workflow: discover projects, import textual .sysml documents, and download a
SysON document back to a file.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

import requests

GRAPHQL_ENDPOINT = "/api/graphql"
GRAPHQL_UPLOAD_ENDPOINT = "/api/graphql/upload"
DOWNLOAD_ENDPOINT = "/api/editingcontexts/{editing_context_id}/documents/{document_id}"

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
    response = requests.post(graphql_url(url), json={"query": query, "variables": variables or {}}, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"GraphQL HTTP {response.status_code}: {response.text[:2000]}")
    data = response.json()
    if data.get("errors"):
        raise RuntimeError("GraphQL errors: " + json.dumps(data["errors"], indent=2))
    return data


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
            "text": text,
        }
    }
    return post_graphql(url, INSERT_TEXTUAL_SYSML_MUTATION, variables)


def download_document(url: str, project_id: str, document_id: str, output_path: Path) -> None:
    context_id = editing_context(url, project_id)
    response = requests.get(download_url(url, context_id, document_id), headers={"Accept": "text/plain"}, timeout=120)
    if response.status_code != 200:
        raise RuntimeError(f"Download HTTP {response.status_code}: {response.text[:2000]}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8080", help="SysON base URL")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-projects")

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
