#!/usr/bin/env python3
"""Run the read-only DE4SDV semantic MCP server over stdio."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.mcp_server import create_mcp_server
from de4sdv.semantic.runtime import build_semantic_runtime


def _value(argument: str | None, environment: str) -> str | None:
    return argument or os.environ.get(environment)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url")
    parser.add_argument("--binding", type=Path)
    parser.add_argument("--expected-git-revision")
    parser.add_argument(
        "--ontology",
        type=Path,
        default=ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml",
    )
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

    service = build_semantic_runtime(
        api_url=str(api_url),
        binding_path=Path(str(binding_value)),
        expected_git_revision=str(expected_git_revision),
        ontology_path=args.ontology,
        api_timeout=args.api_timeout,
    )
    create_mcp_server(service).run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
