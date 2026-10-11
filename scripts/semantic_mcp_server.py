#!/usr/bin/env python3
"""Run the read-only DE4SDV semantic MCP server over stdio.

The server starts from four things: a clean checkout of the deployed commit
(this repository), the deployment's revision binding, the deployed SysML v2
API, and one startup check
(:func:`de4sdv.semantic.deployment_runtime.verify_startup`): right commit,
clean tree, the same ``sai-`` semantic authority recomputed from the
checkout, and a binding that records the served model. Any failure refuses
to start. The first element listing is accepted only when its content equals
the validated export the binding records; otherwise every tool call is
refused.

    --api-url                DE4SDV_SYSML_API_URL
    --binding                DE4SDV_REVISION_BINDING
    --expected-git-revision  DE4SDV_EXPECTED_GIT_SHA

The bound revision's element corpus is cached across restarts in an
identity-bound snapshot (``DE4SDV_SEMANTIC_SNAPSHOT_DIR``, default
``~/.cache/de4sdv/semantic-snapshots``); a miss, or a snapshot that is not
the validated export, loads from the API.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic import corpus_cache  # noqa: E402
from de4sdv.semantic.deployment_runtime import (  # noqa: E402
    StartupCheckError,
    build_deployment_runtime,
)
from de4sdv.semantic.mcp_server import create_mcp_server  # noqa: E402


def _value(argument: str | None, environment: str) -> str | None:
    return argument or os.environ.get(environment)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url")
    parser.add_argument("--binding", type=Path)
    parser.add_argument("--expected-git-revision")
    parser.add_argument("--api-timeout", type=float, default=600.0)
    args = parser.parse_args()

    api_url = _value(args.api_url, "DE4SDV_SYSML_API_URL")
    binding_value = _value(
        str(args.binding) if args.binding is not None else None,
        "DE4SDV_REVISION_BINDING",
    )
    expected_git_revision = _value(
        args.expected_git_revision, "DE4SDV_EXPECTED_GIT_SHA"
    )
    missing = [
        name
        for name, value in (
            ("SysML API URL", api_url),
            ("revision binding", binding_value),
            ("expected Git SHA", expected_git_revision),
        )
        if not value
    ]
    if missing:
        parser.error("missing runtime contract: " + ", ".join(missing))

    try:
        service = build_deployment_runtime(
            ROOT,
            api_url=str(api_url),
            binding_path=Path(str(binding_value)),
            expected_git_revision=str(expected_git_revision),
            api_timeout=args.api_timeout,
        )
    except StartupCheckError as exc:
        # Fail closed: the server never starts on a checkout, binding or
        # semantic authority other than the deployment's.
        parser.error(str(exc))
    print(
        "semantic authority: " + json.dumps(service.authority_status(), sort_keys=True),
        file=sys.stderr,
    )
    # Fast start: a lazy, identity-bound snapshot of the bound revision's
    # element corpus. Installing performs no I/O, so the stdio handshake never
    # waits; the first listing is served from the snapshot when one exists
    # (DE4SDV_SEMANTIC_SNAPSHOT_DIR), else loaded from the API and saved. The
    # served-model guard the runtime installed refuses any other corpus.
    corpus_cache.install_corpus_snapshot(service)
    create_mcp_server(service).run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
