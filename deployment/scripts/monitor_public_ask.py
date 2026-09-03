#!/usr/bin/env python3
"""GET-only health monitor for the public Ask-model viewer."""
from __future__ import annotations

import argparse
import json
import re
import socket
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ASK_URL = "https://viewer.de4sdv.org"
MODEL_STATUS_URL = "https://sysml-api.de4sdv.org/deployment-status.json"
_SHA = re.compile(r"[0-9a-f]{40}")


class MonitorError(RuntimeError):
    """The enabled public Ask service is unhealthy or inconsistent."""


def _get_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "de4sdv-ask-monitor/1"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise MonitorError(f"GET {url} returned {response.status}")
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise MonitorError(f"GET {url} did not return a JSON object")
    return payload


def monitor_public_ask(
    *,
    ask_url: str = ASK_URL,
    model_status_url: str = MODEL_STATUS_URL,
    repo: Path | None = None,
) -> dict[str, str]:
    ask_status = _get_json(f"{ask_url.rstrip('/')}/ask-status.json")
    app_revision = ask_status.get("application_git_commit")
    model_revision = ask_status.get("model_git_commit")
    if not isinstance(app_revision, str) or not _SHA.fullmatch(app_revision):
        raise MonitorError("invalid public Ask application revision")
    if not isinstance(model_revision, str) or not _SHA.fullmatch(model_revision):
        raise MonitorError("invalid public Ask model revision")
    warmup = ask_status.get("semantic_warmup")
    if not isinstance(warmup, dict) or warmup.get("status") != "ready":
        raise MonitorError("semantic warmup is not ready")

    model_status = _get_json(model_status_url)
    baseline = model_status.get("baseline")
    served_model = baseline.get("git_commit") if isinstance(baseline, dict) else None
    if served_model != model_revision:
        raise MonitorError("Ask-model revision differs from the public model API")

    if repo is not None:
        result = subprocess.run(
            [
                "git", "-c", f"safe.directory={repo.resolve()}",
                "-C", str(repo.resolve()), "merge-base", "--is-ancestor",
                app_revision, "origin/main",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise MonitorError("public Ask application revision is not on main")

    return {
        "status": "healthy",
        "application_git_commit": app_revision,
        "model_git_commit": model_revision,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ask-url", default=ASK_URL)
    parser.add_argument("--model-status-url", default=MODEL_STATUS_URL)
    parser.add_argument("--repo", type=Path)
    args = parser.parse_args(argv)

    hostname = urllib.parse.urlparse(args.ask_url).hostname
    if not hostname:
        print("invalid Ask URL", file=sys.stderr)
        return 2
    try:
        socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        print(json.dumps({"status": "not-enabled", "hostname": hostname}))
        return 0

    try:
        result = monitor_public_ask(
            ask_url=args.ask_url,
            model_status_url=args.model_status_url,
            repo=args.repo,
        )
    except (MonitorError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Public Ask monitor failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
