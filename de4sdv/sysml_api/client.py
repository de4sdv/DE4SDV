"""Low-level Systems Modeling API HTTP client.

The transport is extracted from the live-service client proven in DE4SDV PR #36.
It keeps the standard-library-only HTTP boundary while adding pagination,
authentication headers, and a typed error model for production callers.

Throttling: the public API allows 50 requests per 10 seconds. An HTTP 429
response is retried a bounded number of times after waiting the server's
``Retry-After`` (delta seconds or HTTP date) or, without that header, one
rate window. A requested wait above the bound, or a throttle that outlasts
the retries, raises ``ApiError`` with status 429. Other HTTP errors are never
retried.
"""

from __future__ import annotations

import email.utils
import json
import math
import re
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit
from dataclasses import dataclass, field
from typing import Any, Callable

from .errors import ApiError

_NEXT_LINK_RE = re.compile(r'<([^>]+)>\s*;\s*rel="next"')

#: Wait applied to a 429 without ``Retry-After``: one window of the public
#: API rate limit (50 requests per 10 seconds).
DEFAULT_RATE_LIMIT_WAIT_SECONDS = 10.0
#: Retries of one throttled request before the 429 is raised.
DEFAULT_RATE_LIMIT_RETRIES = 3
#: Longest single wait the client accepts; a longer ``Retry-After`` fails.
DEFAULT_MAX_RATE_LIMIT_WAIT_SECONDS = 30.0


def _retry_after_seconds(value: str | None, now: float) -> float | None:
    """Seconds requested by a ``Retry-After`` header, or None when absent/invalid."""
    if value is None or not value.strip():
        return None
    text = value.strip()
    try:
        seconds = float(text)
    except ValueError:
        pass
    else:
        # NaN is unreadable (one rate window applies); infinity exceeds any bound.
        return None if math.isnan(seconds) else max(0.0, seconds)
    try:
        moment = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if moment is None:
        return None
    return max(0.0, moment.timestamp() - now)


@dataclass(frozen=True)
class ApiClient:
    """Small HTTP client for standard SysML v2 API paths."""

    base_url: str
    token: str | None = None
    timeout: float = 30.0
    default_headers: dict[str, str] = field(default_factory=dict)
    max_rate_limit_retries: int = DEFAULT_RATE_LIMIT_RETRIES
    max_rate_limit_wait_seconds: float = DEFAULT_MAX_RATE_LIMIT_WAIT_SECONDS
    sleep: Callable[[float], None] = field(default=time.sleep, repr=False, compare=False)

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
        attempt = 0
        while True:
            request = urllib.request.Request(
                self._url(path), data=data, headers=headers, method=method
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read().decode("utf-8")
                    response_headers = dict(response.headers.items())
                break
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                if exc.code != 429:
                    raise ApiError(method, path, body[:2000], status=exc.code) from exc
                header = exc.headers.get("Retry-After") if exc.headers else None
                requested = _retry_after_seconds(header, time.time())
                wait = DEFAULT_RATE_LIMIT_WAIT_SECONDS if requested is None else requested
                if wait > self.max_rate_limit_wait_seconds:
                    raise ApiError(
                        method,
                        path,
                        f"rate limited; Retry-After {header} exceeds the bounded "
                        f"wait of {self.max_rate_limit_wait_seconds:g} s",
                        status=429,
                    ) from exc
                if attempt >= self.max_rate_limit_retries:
                    raise ApiError(
                        method,
                        path,
                        f"rate limited after {attempt} bounded retries: {body[:1000]}",
                        status=429,
                    ) from exc
                attempt += 1
                self.sleep(wait)
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
