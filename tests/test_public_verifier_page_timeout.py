"""The public verifier reads element pages with their own limit and turns a transport failure into a verdict.

Regression: the post-deploy verification of deploy run 43607286898 (123,361
elements, 2026-11-15) stopped with an uncaught ``TimeoutError``. A
5,000-element page needed 58-62 s against the generic 60 s request limit, and
no fail verdict was written.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "deployment" / "scripts" / "verify_public_api.py"


def _load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _paging_fetch(module: Any, *, pages: int, slow_page: int | None = None, seen: list[tuple[str, Any]]):
    """A fake fetch serving ``pages`` element pages; ``slow_page`` raises the read timeout."""
    served = 0

    def fake_fetch(url: str, *, method: str = "GET", timeout: Any = 60):
        nonlocal served
        seen.append((url, timeout))
        if url.endswith("/elements/known-id"):
            return 200, {}, json.dumps({"@id": "known-id", "declaredName": module.KNOWN_ELEMENT_NAME}).encode()
        served += 1
        if served == slow_page:
            raise TimeoutError("The read operation timed out")
        page = [{"@id": f"e-{served}-{index}"} for index in range(26_000)]
        if served == 1:
            page[0] = {"@id": "known-id", "declaredName": module.KNOWN_ELEMENT_NAME}
        headers = {}
        if served < pages:
            headers["Link"] = (
                "<http://sysml2-api:9000/projects/p/commits/c/elements?"
                f'page%5Bafter%5D={served + 1}>; rel="next"'
            )
        return 200, headers, json.dumps(page).encode()

    return fake_fetch


def _stub_checks_before_pagination(module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "check_tls", lambda base: None)
    monkeypatch.setattr(module, "check_method_allowlist", lambda base: {"POST": 405})
    monkeypatch.setattr(module, "check_status_document", lambda base: {"baseline": {}})
    monkeypatch.setattr(module, "check_model", lambda base, status: {"project": "p", "commit": "c"})
    monkeypatch.setattr(
        module, "wait_for_ask_semantic_runtime", lambda *args, **kwargs: {"warmup": "ready"}
    )


def test_a_page_that_does_not_answer_in_time_names_its_page_and_the_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("verify_public_api_page_timeout")
    seen: list[tuple[str, Any]] = []
    monkeypatch.setattr(module, "fetch", _paging_fetch(module, pages=4, slow_page=3, seen=seen))

    with pytest.raises(module.VerificationError) as caught:
        module.check_pagination_and_known_element(
            "https://sysml-api.de4sdv.org", "p", "c", page_timeout=300
        )

    message = str(caught.value)
    assert "page 3" in message
    assert "300" in message
    assert isinstance(caught.value.__cause__, TimeoutError)


def test_pages_are_read_with_the_page_limit_and_timed(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load("verify_public_api_page_limit")
    seen: list[tuple[str, Any]] = []
    monkeypatch.setattr(module, "fetch", _paging_fetch(module, pages=3, seen=seen))
    page_seconds: list[float] = []

    total = module.check_pagination_and_known_element(
        "https://sysml-api.de4sdv.org", "p", "c", page_seconds=page_seconds
    )

    assert total == 78_000
    page_limits = [timeout for url, timeout in seen if "/elements?" in url]
    assert page_limits == [module.PAGE_READ_TIMEOUT_SECONDS] * 3
    assert module.PAGE_READ_TIMEOUT_SECONDS > 60
    assert len(page_seconds) == 3
    assert all(seconds >= 0 for seconds in page_seconds)


def test_main_writes_a_fail_verdict_when_a_page_times_out(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The whole call path, as the deploy job runs it: a verdict, not a traceback."""
    module = _load("verify_public_api_main_timeout")
    _stub_checks_before_pagination(module, monkeypatch)
    seen: list[tuple[str, Any]] = []
    monkeypatch.setattr(module, "fetch", _paging_fetch(module, pages=4, slow_page=2, seen=seen))
    out = tmp_path / "verify.json"
    monkeypatch.setattr(sys, "argv", ["verify_public_api.py", "--json", str(out)])

    assert module.main() == 1

    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["verdict"] == "fail"
    assert "page 2" in report["error"]
    assert "VERIFICATION FAILED" in capsys.readouterr().err


def test_main_writes_a_fail_verdict_on_any_transport_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _load("verify_public_api_main_transport")
    _stub_checks_before_pagination(module, monkeypatch)

    def reset(base: str, status: Any) -> Any:
        raise ConnectionResetError(104, "Connection reset by peer")

    monkeypatch.setattr(module, "check_model", reset)
    out = tmp_path / "verify.json"
    monkeypatch.setattr(sys, "argv", ["verify_public_api.py", "--json", str(out)])

    assert module.main() == 1

    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["verdict"] == "fail"
    assert "Connection reset" in report["error"]


def test_the_report_records_the_page_limit_and_the_slowest_page(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _load("verify_public_api_main_report")
    _stub_checks_before_pagination(module, monkeypatch)
    seen: list[tuple[str, Any]] = []
    monkeypatch.setattr(module, "fetch", _paging_fetch(module, pages=2, seen=seen))
    out = tmp_path / "verify.json"
    monkeypatch.setattr(
        sys, "argv", ["verify_public_api.py", "--json", str(out), "--page-timeout", "120"]
    )

    assert module.main() == 0

    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["verdict"] == "pass"
    assert report["paginated_elements"] == 52_000
    pagination = report["pagination"]
    assert pagination["pages"] == 2
    assert pagination["page_size"] == module.PAGINATION_PAGE_SIZE
    assert pagination["page_read_timeout_seconds"] == 120
    assert 0 <= pagination["slowest_page_seconds"] <= pagination["total_seconds"]
    assert [timeout for url, timeout in seen if "/elements?" in url] == [120, 120]
