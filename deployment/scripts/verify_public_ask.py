#!/usr/bin/env python3
"""Externally verify the public DE4SDV Ask-model reader path."""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any


class VerificationError(RuntimeError):
    """The public Ask-model contract was not observed."""


def _request(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    origin: str | None = None,
) -> tuple[int, bytes]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"User-Agent": "DE4SDV-public-ask-verifier/1"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if origin is not None:
        headers["Origin"] = origin
    request = urllib.request.Request(
        url, data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _json_request(*args, **kwargs) -> tuple[int, dict[str, Any]]:
    status, body = _request(*args, **kwargs)
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError(
            f"expected JSON response from {args[0]} (HTTP {status})"
        ) from exc
    if not isinstance(payload, dict):
        raise VerificationError(f"expected JSON object from {args[0]}")
    return status, payload


def _deployed_model_revision() -> str:
    status, payload = _json_request(
        "https://sysml-api.de4sdv.org/deployment-status.json"
    )
    if status != 200:
        raise VerificationError(
            f"SysML API deployment status returned HTTP {status}"
        )
    baseline = payload.get("baseline")
    revision = baseline.get("git_commit") if isinstance(baseline, dict) else None
    if not isinstance(revision, str) or len(revision) != 40:
        raise VerificationError("SysML API status has no baseline git_commit")
    return revision


_TLS_READINESS_ATTEMPTS = 12
_TLS_READINESS_DELAY_SECONDS = 5.0


def _tls_ready(base_url: str, *, attempts: int, delay_seconds: float) -> None:
    """Wait for the public TLS endpoint after the proxy has started.

    Caddy can bind 443 before its first TLS handshake is ready, so retry
    only this readiness boundary while retaining normal certificate
    validation.
    """
    request = urllib.request.Request(base_url, method="GET")
    last_error: OSError | None = None
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=30):
                return
        except urllib.error.HTTPError:
            return  # TLS answered; the HTTP status is checked separately
        except (urllib.error.URLError, OSError) as exc:
            last_error = exc
        if attempts > 1:
            time.sleep(delay_seconds)
    raise VerificationError(
        f"TLS endpoint not ready after {attempts} attempts: {last_error}"
    ) from last_error


def verify_public_ask(
    base_url: str,
    *,
    application_sha: str,
    model_sha: str | None = None,
    live_query: bool = False,
    tls_attempts: int = _TLS_READINESS_ATTEMPTS,
) -> dict[str, str]:
    base_url = base_url.rstrip("/")
    _tls_ready(
        base_url,
        attempts=tls_attempts,
        delay_seconds=_TLS_READINESS_DELAY_SECONDS,
    )
    model_sha = model_sha or _deployed_model_revision()

    status_code, status = _json_request(f"{base_url}/ask-status.json")
    if status_code != 200:
        raise VerificationError(f"Ask status returned HTTP {status_code}")
    if status.get("application_git_commit") != application_sha:
        raise VerificationError("public Ask application revision mismatch")
    if status.get("model_git_commit") != model_sha:
        raise VerificationError("public Ask model revision mismatch")
    warmup = status.get("semantic_warmup")
    if not isinstance(warmup, dict) or warmup.get("status") != "ready":
        raise VerificationError("public Ask semantic warmup is not ready")

    root_code, root = _request(f"{base_url}/")
    if root_code != 200 or b"__DE4SDV_VIEWER_SERVER__" not in root:
        raise VerificationError("dynamic viewer marker is missing")
    asset_code, asset = _request(f"{base_url}/assets/viewer.js")
    if asset_code != 200 or b"function renderAskAnswer" not in asset:
        raise VerificationError("safe structured answer renderer is missing")

    method_code, _ = _request(f"{base_url}/", method="BREW")
    if method_code != 405:
        raise VerificationError("unknown HTTP method was not rejected")

    missing_origin_code, _ = _json_request(
        f"{base_url}/ask",
        method="POST",
        payload={"element": "missing", "question": "q"},
    )
    if missing_origin_code != 403:
        raise VerificationError("Ask accepted a request without its Origin")

    unknown_code, _ = _json_request(
        f"{base_url}/ask",
        method="POST",
        origin=base_url,
        payload={"element": "missing", "question": "q"},
    )
    if unknown_code != 404:
        raise VerificationError("Ask did not reject an unknown model element")

    result = {
        "application_git_commit": application_sha,
        "model_git_commit": model_sha,
        "live_query": "skipped",
    }
    if live_query:
        answer_code, answer = _json_request(
            f"{base_url}/ask",
            method="POST",
            origin=base_url,
            payload={
                "element": "evidenceObjective",
                "question": "Which requirements do you verify?",
            },
        )
        if answer_code != 200 or not str(answer.get("answer") or "").strip():
            raise VerificationError(
                f"live grounded query failed with HTTP {answer_code}"
            )
        source = str(answer.get("method_context_source") or "")
        if source != "api":
            raise VerificationError(
                f"live query was not API-grounded: {source or 'missing source'}"
            )
        result["live_query"] = "passed"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://viewer.de4sdv.org")
    parser.add_argument("--application-sha", required=True)
    parser.add_argument("--model-sha")
    parser.add_argument("--live-query", action="store_true")
    parser.add_argument("--element", default="evidenceObjective")
    args = parser.parse_args(argv)
    try:
        result = verify_public_ask(
            args.base_url,
            application_sha=args.application_sha,
            model_sha=args.model_sha,
            live_query=args.live_query,
        )
    except (OSError, VerificationError) as exc:
        print(f"Public Ask verification failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
