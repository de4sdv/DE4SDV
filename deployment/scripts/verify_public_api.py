#!/usr/bin/env python3
"""External verification for the DE4SDV Experimental Read-Only API.

Proves, from OUTSIDE the server, that:
  - HTTPS works with a valid certificate;
  - GET/HEAD work and OPTIONS is answered;
  - the proxy enforces a strict method allowlist: POST/PUT/PATCH/DELETE AND
    at least one otherwise-unlisted nonstandard method are rejected 405;
  - the machine-readable deployment-status document is present and honest;
  - the deployment-specific project/commit from the status tuple is served;
  - the known element reqCommandEmergencyBraking is retrievable by its API
    UUID through the standard element path;
  - full-model pagination exceeds 50,000 elements.

Exits nonzero on any failure. Read-only: the script never sends a mutation
payload beyond the method probes (which carry no body and must be rejected).

Usage:
  python3 verify_public_api.py [--base-url https://sysml-api.de4sdv.org] \
      [--json OUT.json] [--skip-full-pagination]
"""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
from pathlib import Path
from typing import Any
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit

KNOWN_ELEMENT_NAME = "reqCommandEmergencyBraking"
MUTATION_METHODS = ("POST", "PUT", "PATCH", "DELETE")
# A deliberately nonstandard/extension method: if the proxy used a deny-list,
# an unknown verb like this could slip through to the upstream API.
NONSTANDARD_METHOD = "BREW"


class VerificationError(RuntimeError):
    pass


def _same_origin(link: str, base_url: str) -> str:
    """Reconnect server-generated pagination links to the configured origin.

    The API builds absolute next-links from the request Host header, which
    Caddy rewrites to the container-internal name (sysml2-api:9000). A
    public client cannot resolve that name; the service is whatever
    base_url is. Keep the linked path+query, swap the origin.
    """
    linked = urlsplit(link)
    configured = urlsplit(base_url)
    if (linked.scheme, linked.netloc) == (configured.scheme, configured.netloc):
        return link
    return urlunsplit(
        (configured.scheme, configured.netloc, linked.path, linked.query, "")
    )


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


def check_method_allowlist(base_url: str) -> dict[str, int]:
    """Positive allowlist contract: only GET/HEAD/OPTIONS may pass."""
    verdicts: dict[str, int] = {}
    for method in (*MUTATION_METHODS, NONSTANDARD_METHOD):
        status, _headers, _body = fetch(f"{base_url}/projects", method=method)
        require(status == 405, f"{method} was not rejected 405 by the proxy (HTTP {status})")
        verdicts[method] = status
    for method in ("GET", "HEAD", "OPTIONS"):
        status, _headers, _body = fetch(f"{base_url}/projects", method=method)
        require(status < 500, f"allowed method {method} answered {status}")
        verdicts[method] = status
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

    result: dict[str, Any] = {"project": project_id, "commit": commit_id}
    return result


def check_pagination_and_known_element(
    base_url: str, project_id: str, commit_id: str
) -> int:
    """Follow rel=next Link headers; prove pagination and the known element."""
    url: str | None = f"{base_url}/projects/{project_id}/commits/{commit_id}/elements"
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
            url = _same_origin(link[start:end], base)
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

    report: dict[str, Any] = {
        "base_url": base,
        "checked_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        check_tls(base)
        report["https"] = True

        report["method_allowlist"] = check_method_allowlist(base)

        status_doc = check_status_document(base)
        report["status_document"] = status_doc

        model = check_model(base, status_doc)
        report["model"] = model

        if not args.skip_full_pagination:
            total = check_pagination_and_known_element(base, model["project"], model["commit"])
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
