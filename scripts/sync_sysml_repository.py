#!/usr/bin/env python3
"""Bootstrap/sync the DE4SDV SysML v2 API repository pilot.

This is intentionally small. It proves the repository boundary and records real
SysML v2 API project/commit metadata in Git-tracked manifests. It does not claim
to solve textual SysML import/export or SysON view rendering yet.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_API_URL = "http://127.0.0.1:9000"
DEFAULT_PROJECT = "DE4SDV"
DEFAULT_BRANCH = "main"
VIEW_MANIFESTS = [
    Path("textual-notation-of-model/views/system-context/manifest.json"),
    Path("textual-notation-of-model/views/lifecycle-engineering-system/manifest.json"),
]
SYNC_FILE = Path("textual-notation-of-model/sync/last-synced-commit.json")


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
        req = urllib.request.Request(self._url(path), data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {path} failed with HTTP {exc.code}: {body[:2000]}") from exc
        if not raw:
            return None
        return json.loads(raw)


def identified(element_id: str) -> dict[str, str]:
    return {"@id": element_id}


def package_element(
    element_id: str,
    name: str,
    *,
    qualified_name: str | None = None,
    owner_id: str | None = None,
    owned_ids: list[str] | None = None,
) -> dict[str, Any]:
    owned = [identified(item) for item in (owned_ids or [])]
    owner = identified(owner_id) if owner_id else None
    return {
        "@type": "Package",
        "@id": element_id,
        "aliasIds": [],
        "declaredName": name,
        "declaredShortName": None,
        "documentation": [],
        "elementId": element_id,
        "filterCondition": [],
        "importedMembership": [],
        "isImpliedIncluded": False,
        "isLibraryElement": False,
        "member": owned,
        "membership": [],
        "name": name,
        "ownedAnnotation": [],
        "ownedElement": owned,
        "ownedImport": [],
        "ownedMember": owned,
        "ownedMembership": [],
        "ownedRelationship": [],
        "owner": owner,
        "owningMembership": None,
        "owningNamespace": owner,
        "owningRelationship": None,
        "qualifiedName": qualified_name or name,
        "shortName": None,
        "textualRepresentation": [],
    }


def context_payload() -> list[dict[str, Any]]:
    root_id = str(uuid.uuid4())
    context_id = str(uuid.uuid4())
    system1_id = str(uuid.uuid4())
    system2_id = str(uuid.uuid4())
    system3_id = str(uuid.uuid4())
    lifecycle_id = str(uuid.uuid4())

    root = package_element(
        root_id,
        "DE4SDV",
        owned_ids=[context_id, lifecycle_id],
    )
    context = package_element(
        context_id,
        "Context",
        qualified_name="DE4SDV::Context",
        owner_id=root_id,
        owned_ids=[system1_id, system2_id, system3_id],
    )
    system1 = package_element(
        system1_id,
        "ConfigurableSDVProductLine",
        qualified_name="DE4SDV::Context::ConfigurableSDVProductLine",
        owner_id=context_id,
    )
    system2 = package_element(
        system2_id,
        "DE4SDV_LifecycleEngineeringSystem",
        qualified_name="DE4SDV::Context::DE4SDV_LifecycleEngineeringSystem",
        owner_id=context_id,
    )
    system3 = package_element(
        system3_id,
        "DE4SDV_OpenInnovationEcosystem",
        qualified_name="DE4SDV::Context::DE4SDV_OpenInnovationEcosystem",
        owner_id=context_id,
    )
    lifecycle = package_element(
        lifecycle_id,
        "LifecycleEngineeringSystem",
        qualified_name="DE4SDV::LifecycleEngineeringSystem",
        owner_id=root_id,
    )
    return [root, context, system1, system2, system3, lifecycle]


def find_project(client: ApiClient, name: str) -> dict[str, Any] | None:
    projects = client.request("GET", "/projects")
    for project in projects:
        if project.get("name") == name:
            return project
    return None


def ensure_project(client: ApiClient, name: str, *, dry_run: bool) -> dict[str, Any]:
    project = find_project(client, name)
    if project:
        return project
    payload = {
        "@type": "Project",
        "name": name,
        "description": "DE4SDV live SysML v2 API repository pilot for the ASELCM context model.",
    }
    if dry_run:
        return {"@id": "dry-run-project-id", "name": name, "defaultBranch": {"@id": "dry-run-branch-id"}}
    return client.request("POST", "/projects", payload)


def latest_commit(client: ApiClient, project_id: str) -> dict[str, Any] | None:
    commits = client.request("GET", f"/projects/{project_id}/commits")
    if not commits:
        return None
    return commits[-1]


def create_bootstrap_commit(client: ApiClient, project_id: str, *, dry_run: bool) -> dict[str, Any]:
    elements = context_payload()
    payload = {
        "@type": "Commit",
        "name": "bootstrap DE4SDV context model",
        "description": "Bootstrap ASELCM System 1-2-3 context packages for the DE4SDV SysML v2 API pilot.",
        "change": [{"@type": "DataVersion", "payload": element} for element in elements],
    }
    if dry_run:
        return {
            "@id": "dry-run-commit-id",
            "name": payload["name"],
            "description": payload["description"],
            "previousCommit": None,
        }
    return client.request("POST", f"/projects/{project_id}/commits", payload)


def read_roots(client: ApiClient, project_id: str, commit_id: str) -> list[dict[str, Any]]:
    return client.request("GET", f"/projects/{project_id}/commits/{commit_id}/roots")


def update_json_file(path: Path, data: dict[str, Any], *, dry_run: bool) -> bool:
    before = path.read_text() if path.exists() else None
    after = json.dumps(data, indent=2) + "\n"
    changed = before != after
    if changed and not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(after)
    return changed


def update_manifests(project: dict[str, Any], commit: dict[str, Any], *, branch: str, dry_run: bool) -> list[Path]:
    changed: list[Path] = []
    for path in VIEW_MANIFESTS:
        data = json.loads(path.read_text())
        data["status"] = "api-bootstrap-synced"
        data["sysml_project"] = project["name"]
        data["sysml_project_id"] = project["@id"]
        data["sysml_branch"] = branch
        data["sysml_commit"] = commit["@id"]
        data["sync_source"] = "SysML v2 API Services pilot"
        data.setdefault("notes", [])
        note = "Synced to a real SysML v2 API project/commit; rendered SVG remains a bootstrap placeholder."
        if note not in data["notes"]:
            data["notes"].append(note)
        if update_json_file(path, data, dry_run=dry_run):
            changed.append(path)
    sync_data = {
        "sysml_project": project["name"],
        "sysml_project_id": project["@id"],
        "sysml_branch": branch,
        "sysml_commit": commit["@id"],
        "commit_name": commit.get("name"),
        "commit_description": commit.get("description"),
        "source": "SysML v2 API Services pilot",
        "limitations": [
            "Textual .sysml export/import is not implemented in this MVP.",
            "SysON rendering/export is not connected in this MVP.",
        ],
    }
    if update_json_file(SYNC_FILE, sync_data, dry_run=dry_run):
        changed.append(SYNC_FILE)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary")
    args = parser.parse_args()

    client = ApiClient(args.api_url)
    project = ensure_project(client, args.project, dry_run=args.dry_run)
    commit = latest_commit(client, project["@id"]) if not args.dry_run else None
    created_commit = False
    if commit is None:
        commit = create_bootstrap_commit(client, project["@id"], dry_run=args.dry_run)
        created_commit = True

    roots = [] if args.dry_run else read_roots(client, project["@id"], commit["@id"])
    changed = update_manifests(project, commit, branch=args.branch, dry_run=args.dry_run)
    summary = {
        "api_url": args.api_url,
        "project": project,
        "commit": commit,
        "created_commit": created_commit,
        "root_count": len(roots),
        "root_names": [root.get("qualifiedName") or root.get("name") for root in roots],
        "changed_files": [str(path) for path in changed],
        "dry_run": args.dry_run,
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"project: {project['name']} ({project['@id']})")
        print(f"commit: {commit['@id']} ({commit.get('name')})")
        print(f"created_commit: {created_commit}")
        print(f"roots: {len(roots)} {summary['root_names']}")
        if changed:
            print("changed files:")
            for path in changed:
                print(f"- {path}")
        else:
            print("changed files: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
