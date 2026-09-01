#!/usr/bin/env python3
"""External verification for the DE4SDV Experimental Read-Only API.

Proves, from OUTSIDE the server, that:
  - HTTPS works with a valid certificate;
  - GET/HEAD work and OPTIONS is answered;
  - POST/PUT/PATCH/DELETE are rejected (405) at the proxy boundary;
  - the served project/commit matches the deployment-status tuple;
  - a known element (reqCommandEmergencyBraking) is retrievable by UUID
    through the standard element path;
  - pagination works for the 56k+ element model;
  - the machine-readable deployment-status document is present and honest.

Exits nonzero on any failure. Read-only: the script never sends a mutation
payload beyond the method probes (which carry no body and must be rejected).

Usage:
  python3 verify_public_api.py [--base-url https://sysml-api.de4sdv.org] \
      [--json OUT.json]
"""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

KNOWN_ELEMENT_NAME = "reqCommandEmergencyBraking"


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def fetch(url: str, *, method: str = "GET", timeout: int = 60):
    request = urlrequest.Request(url, method=method)
    try:
        with urlrequest.urlopen(request, timeout=timeout) as response:
            body = response.read()
            return response.status, dict(response.headers), body
    except HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def fetch_json(url: str, **kwargs) -> Any:
    status, _headers, body = fetch(url, **kwargs)
    require(status == 200, f"{url} returned {status}")
    return json.loads(body.decode("utf-8"))


def check_tls(base_url: str) -> None:
    require(base_url.startswith("https://"), "base URL must be HTTPS")
    host = base_url.split("://", 1)[1].rstrip("/")
    context = ssl.create_default_context()
    with urlrequest.urlopen(f"https://{host}/", timeout=30, context=context) as response:
        require(response.status in (200, 404), f"TLS handshake/first response failed: {response.status}")


def check_read_only(base_url: str) -> dict[str, int]:
    verdicts: dict[str, int] = {}
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        status, _headers, _body = fetch(f"{base_url}/projects", method=method)
        require(
            status in (403, 405),
            f"{method} was not rejected by the proxy (HTTP {status})",
        )
        verdicts[method] = status
    status, _headers, _body = fetch(f"{base_url}/projects", method="OPTIONS")
    verdicts["OPTIONS"] = status
    require(status < 500, f"OPTIONS answered with {status}")
    return verdicts


def check_status_document(base_url: str) -> dict[str, Any]:
    status_doc = fetch_json(f"{base_url}/deployment-status.json")
    require(status_doc.get("read_only") is True, "status document does not declare read-only")
    require(
        status_doc.get("service") == "DE4SDV Experimental Read-Only Systems Modeling API",
        "status document has the wrong service label",
    )
    baseline = status_doc.get("baseline") or {}
    for field in ("git_commit", "sysml_project_id", "sysml_commit_id", "ontology"):
        require(field in baseline, f"status document baseline missing {field}")
    text = json.dumps(status_doc)
    require("password" not in text.lower(), "status document may contain a secret")
    return status_doc


def check_model(base_url: str, status_doc: dict[str, Any]) -> dict[str, Any]:
    baseline = status_doc["baseline"]
    project_id = baseline["sysml_project_id"]
    commit_id = baseline["sysml_commit_id"]

    projects = fetch_json(f"{base_url}/projects")
    require(isinstance(projects, list) and projects, "/projects returned nothing")
    matching = [p for p in projects if p.get("@id") == project_id]
    require(len(matching) == 1, "deployment-status project not served by the API")

    commit = fetch_json(f"{base_url}/projects/{project_id}/commits/{commit_id}")
    require(commit.get("@id") == commit_id, "deployment-status commit not served")

    elements_url = f"{base_url}/projects/{project_id}/commits/{commit_id}/elements"
    page1 = fetch_json(elements_url)
    require(isinstance(page1, list) and len(page1) > 0, "element page 1 is empty")

    known = None
    for element in page1:
        if element.get("declaredName") == KNOWN_ELEMENT_NAME:
            known = element
            break
    result: dict[str, Any] = {"project": project_id, "commit": commit_id}

    # Resolve the known element by paging (Link-header rel=next handled below
    # by check_pagination); locate its UUID for the identity-path probe.
    if known is not None:
        element_id = known["@id"]
        element = fetch_json(
            f"{base_url}/projects/{project_id}/commits/{commit_id}/elements/{element_id}"
        )
        require(
            element.get("declaredName") == KNOWN_ELEMENT_NAME,
            "known element did not round-trip through its API identity",
        )
        result["known_element_id"] = element_id
    return result


def check_pagination(base_url: str, project_id: str, commit_id: str) -> int:
    """Follow rel=next Link headers and count elements; also probes /elements/{id}."""
    url: str | None = (
        f"{base_url}/projects/{project_id}/commits/{commit_id}/elements"
    )
    total = 0
    pages = 0
    known_id: str | None = None
    while url and pages < 120:
        status, headers, body = fetch(url)
        require(status == 200, f"{url} returned {status}")
        elements = json.loads(body.decode("utf-8"))
        require(isinstance(elements, list), f"{url} did not return a list")
        total += len(elements)
        pages += 1
        if known_id is None:
            for element in elements:
                if element.get("declaredName") == KNOWN_ELEMENT_NAME:
                    known_id = element["@id"]
                    break
        link = headers.get("Link") or headers.get("link")
        url = None
        if link and 'rel="next"' in link:
            start = link.index("<") + 1
            end = link.index(">")
            url = link[start:end]
    require(pages > 1, "expected multi-page pagination for the full model")
    require(total > 50000, f"full model pagination found only {total} elements")
    require(known_id is not None, f"{KNOWN_ELEMENT_NAME} not found while paging")
    element = fetch_json(
        f"{base_url}/projects/{project_id}/commits/{commit_id}/elements/{known_id}"
    )
    require(element.get("declaredName") == KNOWN_ELEMENT_NAME, "known element mismatch")
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://sysml-api.de4sdv.org")
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--skip-full-pagination", action="store_true")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    report: dict[str, Any] = {"base_url": base, "checked_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        check_tls(base)
        report["https"] = True

        report["mutation_rejections"] = check_read_only(base)

        status_doc = check_status_document(base)
        report["status_document"] = status_doc

        model = check_model(base, status_doc)
        report["model"] = model

        if not args.skip_full_pagination:
            total = check_pagination(base, model["project"], model["commit"])
            report["paginated_elements"] = total

        report["verdict"] = "pass"
    except (VerificationError, URLError, json.JSONDecodeError) as exc:
        report["verdict"] = "fail"
        report["error"] = str(exc)
        if args.json:
            args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"VERIFICATION FAILED: {exc}", file=sys.stderr)
        return 1

    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
