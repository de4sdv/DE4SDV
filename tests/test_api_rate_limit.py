"""Bounded HTTP 429 / Retry-After handling in the SysML API client.

The public SysML v2 API limits clients to 50 requests per 10 seconds. A
throttled request is retried a bounded number of times, waiting what the
server asks for (``Retry-After`` seconds or HTTP date) or one rate window when
the header is absent. A wait longer than the bound, or a throttle that
outlasts the retries, fails as an ``ApiError`` with HTTP status 429; other
HTTP errors are never retried.
"""

from __future__ import annotations

import email.utils
import io
import json
import urllib.error
from typing import Any

import pytest

from de4sdv.sysml_api.client import DEFAULT_RATE_LIMIT_WAIT_SECONDS, ApiClient
from de4sdv.sysml_api.errors import ApiError


class _Response:
    def __init__(self, body: Any, headers: dict[str, str] | None = None) -> None:
        self._body = json.dumps(body).encode()
        self.headers = headers or {}

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


def _http_error(url: str, status: int, headers: dict[str, str] | None = None) -> urllib.error.HTTPError:
    message = email.message.Message()
    for key, value in (headers or {}).items():
        message[key] = value
    return urllib.error.HTTPError(url, status, "throttled", message, io.BytesIO(b"slow down"))


class _Script:
    """Replays one scripted outcome per request; records URLs and waits."""

    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = list(outcomes)
        self.urls: list[str] = []
        self.waits: list[float] = []

    def urlopen(self, request: Any, timeout: float | None = None) -> _Response:
        self.urls.append(request.full_url)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, tuple):
            status, headers = outcome
            raise _http_error(request.full_url, status, headers)
        return outcome

    def sleep(self, seconds: float) -> None:
        self.waits.append(seconds)


def _client(script: _Script, monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> ApiClient:
    monkeypatch.setattr("de4sdv.sysml_api.client.urllib.request.urlopen", script.urlopen)
    return ApiClient("http://api.test", sleep=script.sleep, **kwargs)


def test_throttled_request_waits_retry_after_seconds_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _Script([(429, {"Retry-After": "2"}), _Response({"ok": True})])
    client = _client(script, monkeypatch)

    assert client.request("GET", "/projects") == {"ok": True}
    assert script.waits == [2.0]
    assert len(script.urls) == 2


def test_throttle_without_retry_after_waits_one_rate_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _Script([(429, {}), _Response([1])])
    client = _client(script, monkeypatch)

    assert client.request("GET", "/projects") == [1]
    assert DEFAULT_RATE_LIMIT_WAIT_SECONDS == 10.0
    assert script.waits == [DEFAULT_RATE_LIMIT_WAIT_SECONDS]


def test_retry_after_http_date_in_the_past_retries_without_waiting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    past = email.utils.formatdate(0, usegmt=True)
    script = _Script([(429, {"Retry-After": past}), _Response({"ok": 1})])
    client = _client(script, monkeypatch)

    assert client.request("GET", "/projects") == {"ok": 1}
    assert script.waits == [0.0]


def test_persistent_throttle_fails_after_bounded_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _Script([(429, {"Retry-After": "1"})] * 4)
    client = _client(script, monkeypatch, max_rate_limit_retries=3)

    with pytest.raises(ApiError) as raised:
        client.request("GET", "/projects")
    assert raised.value.status == 429
    assert script.waits == [1.0, 1.0, 1.0]
    assert len(script.urls) == 4


def test_retry_after_beyond_the_bound_fails_without_waiting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _Script([(429, {"Retry-After": "3600"})])
    client = _client(script, monkeypatch, max_rate_limit_wait_seconds=30.0)

    with pytest.raises(ApiError) as raised:
        client.request("GET", "/projects")
    assert raised.value.status == 429
    assert "3600" in str(raised.value)
    assert script.waits == []


@pytest.mark.parametrize("status", [400, 404, 500, 503])
def test_other_http_errors_are_not_retried(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    script = _Script([(status, {"Retry-After": "1"})])
    client = _client(script, monkeypatch)

    with pytest.raises(ApiError) as raised:
        client.request("GET", "/projects")
    assert raised.value.status == status
    assert script.waits == []
    assert len(script.urls) == 1


def test_pagination_retries_only_the_throttled_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    next_link = "http://api.test/elements?page%5Bafter%5D=T"
    script = _Script(
        [
            _Response(["a"], {"Link": f'<{next_link}>; rel="next"'}),
            (429, {"Retry-After": "0"}),
            _Response(["b"]),
        ]
    )
    client = _client(script, monkeypatch)

    assert client.get_all("/elements") == ["a", "b"]
    assert script.urls == ["http://api.test/elements", next_link, next_link]
    assert script.waits == [0.0]


@pytest.mark.parametrize("value", ["nan", "NaN", "soon"])
def test_an_unreadable_retry_after_waits_one_rate_window(
    value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = _Script([(429, {"Retry-After": value}), _Response({"ok": True})])
    client = _client(script, monkeypatch)

    assert client.request("GET", "/projects") == {"ok": True}
    assert script.waits == [DEFAULT_RATE_LIMIT_WAIT_SECONDS]
