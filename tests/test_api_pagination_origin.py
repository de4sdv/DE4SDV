"""Pagination next-links must be followed against the configured origin.

The SysML v2 API builds absolute ``rel=next`` pagination links from the
request Host header. On the deploy host the allow-listed Host is the
container-internal name (``sysml2-api:9000``), which the host cannot
resolve; the server is reached at the configured base URL (the bridge IP).
Regression: deploy run 33626421479 died mid-import with
``GET http://sysml2-api:9000/...`` -> "Temporary failure in name resolution".
"""

from __future__ import annotations

import json
import urllib.error
from typing import Any

import pytest

from de4sdv.sysml_api.client import ApiClient


class _FakeResponse:
    def __init__(self, body: bytes, headers: dict[str, str]) -> None:
        self._body = body
        self.headers = headers

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


def test_get_all_rewrites_foreign_origin_next_links_to_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A next-link pointing at an unresolvable internal name is followed
    against the configured origin, keeping path and query."""
    client = ApiClient("http://172.18.0.3:9000", default_headers={"Host": "sysml2-api:9000"})
    pages = [
        ("http://sysml2-api:9000/projects/p/commits/c/elements", ["first"]),
        (
            "http://sysml2-api:9000/projects/p/commits/c/elements?page%5Bafter%5D=TOKEN",
            ["second"],
        ),
    ]
    requested: list[str] = []

    def fake_urlopen(request: Any, timeout: float | None = None) -> _FakeResponse:
        url = request.full_url
        requested.append(url)
        if "after" not in url:
            next_link = pages[1][0]
            return _FakeResponse(
                json.dumps(["first"]).encode(),
                {"Link": f'<{next_link}>; rel="next"'},
            )
        return _FakeResponse(json.dumps(["second"]).encode(), {})

    monkeypatch.setattr("de4sdv.sysml_api.client.urllib.request.urlopen", fake_urlopen)

    result = client.get_all("projects/p/commits/c/elements")

    assert result == ["first", "second"]
    assert requested[0].startswith("http://172.18.0.3:9000/")
    # The foreign-origin next URL was re-connected to the configured origin.
    assert requested[1].startswith("http://172.18.0.3:9000/")
    assert "page%5Bafter%5D=TOKEN" in requested[1]
    assert not any(u.startswith("http://sysml2-api:9000") for u in requested)


def test_get_all_keeps_same_origin_next_links_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the link origin equals the configured origin (CI: 127.0.0.1), the
    URL is followed verbatim."""
    client = ApiClient("http://127.0.0.1:9000")
    requested: list[str] = []

    def fake_urlopen(request: Any, timeout: float | None = None) -> _FakeResponse:
        url = request.full_url
        requested.append(url)
        if "after" not in url:
            return _FakeResponse(
                json.dumps(["page1"]).encode(),
                {"Link": '<http://127.0.0.1:9000/projects/p/commits/c/elements?page%5Bafter%5D=X>; rel="next"'},
            )
        return _FakeResponse(json.dumps(["page2"]).encode(), {})

    monkeypatch.setattr("de4sdv.sysml_api.client.urllib.request.urlopen", fake_urlopen)

    assert client.get_all("projects/p/commits/c/elements") == ["page1", "page2"]
    assert requested[1] == (
        "http://127.0.0.1:9000/projects/p/commits/c/elements?page%5Bafter%5D=X"
    )


def test_same_origin_helper_rewrites_foreign_links() -> None:
    """The public verifier must reconnect next-links to the public origin."""
    import importlib.util
    from pathlib import Path

    script = Path(__file__).resolve().parents[1] / "deployment" / "scripts" / "verify_public_api.py"
    spec = importlib.util.spec_from_file_location("verify_public_api", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert (
        module._same_origin(
            "http://sysml2-api:9000/projects/p/commits/c/elements?page%5Bafter%5D=T",
            "https://sysml-api.de4sdv.org",
        )
        == "https://sysml-api.de4sdv.org/projects/p/commits/c/elements?page%5Bafter%5D=T"
    )
    # Same-origin links pass through untouched.
    same = "https://sysml-api.de4sdv.org/projects/p/commits/c/elements?x=1"
    assert module._same_origin(same, "https://sysml-api.de4sdv.org") == same
