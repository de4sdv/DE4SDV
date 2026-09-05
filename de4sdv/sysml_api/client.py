"""Low-level Systems Modeling API HTTP client.

The transport is extracted from the live-service client proven in DE4SDV PR #36.
It keeps the standard-library-only HTTP boundary while adding pagination,
authentication headers, and a typed error model for production callers.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit
from dataclasses import dataclass, field
from typing import Any

from .errors import ApiError

_NEXT_LINK_RE = re.compile(r'<([^>]+)>\s*;\s*rel="next"')


@dataclass(frozen=True)
class ApiClient:
    """Small HTTP client for standard SysML v2 API paths."""

    base_url: str
    token: str | None = None
    timeout: float = 30.0
    default_headers: dict[str, str] = field(default_factory=dict)

    def _url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            # Absolute URLs come from server-generated pagination links,
            # which the API builds from the request Host header. On direct
            # (non-proxied) calls that Host is a container-internal name
            # (e.g. sysml2-api:9000) that the caller cannot resolve; the
            # server itself is whatever base_url points at. Reconnect to
            # the configured origin and keep the linked path+query.
            linked = urlsplit(path)
            configured = urlsplit(self.base_url)
            if (linked.scheme, linked.netloc) != (configured.scheme, configured.netloc):
                return urlunsplit(
                    (configured.scheme, configured.netloc, linked.path, linked.query, "")
                )
            return path
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def request_with_headers(
        self,
        method: str,
        path: str,
        payload: Any | None = None,
    ) -> tuple[Any, dict[str, str]]:
        data = None
        headers = {"Accept": "application/json", **self.default_headers}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self._url(path), data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                response_headers = dict(response.headers.items())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ApiError(method, path, body[:2000], status=exc.code) from exc
        except urllib.error.URLError as exc:
            raise ApiError(method, path, str(exc.reason)) from exc
        if not raw:
            return None, response_headers
        try:
            return json.loads(raw), response_headers
        except json.JSONDecodeError as exc:
            raise ApiError(method, path, f"invalid JSON response: {exc}") from exc

    def request(self, method: str, path: str, payload: Any | None = None) -> Any:
        """Perform one API request and decode its JSON body."""
        body, _headers = self.request_with_headers(method, path, payload)
        return body

    def get_all(self, path: str) -> list[Any]:
        """GET every page linked through an HTTP ``rel=next`` header."""
        results: list[Any] = []
        next_path: str | None = path
        visited: set[str] = set()
        while next_path is not None:
            url = self._url(next_path)
            if url in visited:
                raise ApiError("GET", next_path, "pagination cycle detected")
            visited.add(url)
            body, headers = self.request_with_headers("GET", next_path)
            page = body.get("items", []) if isinstance(body, dict) else body
            if not isinstance(page, list):
                raise ApiError("GET", next_path, "expected a JSON list page")
            results.extend(page)
            link = headers.get("Link") or headers.get("link") or ""
            match = _NEXT_LINK_RE.search(link)
            next_path = match.group(1) if match else None
        return results
