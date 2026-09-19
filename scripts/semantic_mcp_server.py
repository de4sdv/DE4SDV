#!/usr/bin/env python3
"""Run the read-only DE4SDV semantic MCP server over stdio.

Semantic authority is selected explicitly (O3):

    --semantic-authority legacy|o3      DE4SDV_SEMANTIC_AUTHORITY
    --o3-authority-bundle <path>        DE4SDV_O3_AUTHORITY_BUNDLE
    --o3-authority-bundle-id <o3b-...>  DE4SDV_O3_AUTHORITY_BUNDLE_ID

The default is legacy authority. An explicit O3 request is verified at
startup (exact revision, revision binding, closed bundle attestation,
activation eligibility); any failure refuses to start — there is no
fallback to legacy. See docs/method-conformance/o3/ for the activation and
rollback procedures.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic import corpus_cache  # noqa: E402
from de4sdv.semantic.authority_selection import (  # noqa: E402
    AuthoritySelectionError,
    build_selected_semantic_runtime,
)
from de4sdv.semantic.mcp_server import create_mcp_server  # noqa: E402
from de4sdv.semantic.o3_bundle import O3BundleError  # noqa: E402


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
    parser.add_argument(
        "--semantic-authority",
        help="explicit semantic authority: legacy (default) or o3",
    )
    parser.add_argument(
        "--o3-authority-bundle",
        help="path to the accepted closed O3 authority bundle JSON",
    )
    parser.add_argument(
        "--o3-authority-bundle-id",
        help="exact accepted bundle id (o3b-...) the selection is bound to",
    )
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
        service, selection = build_selected_semantic_runtime(
            api_url=str(api_url),
            binding_path=Path(str(binding_value)),
            expected_git_revision=str(expected_git_revision),
            ontology_path=args.ontology,
            api_timeout=args.api_timeout,
            authority=args.semantic_authority,
            bundle_path=args.o3_authority_bundle,
            bundle_id=args.o3_authority_bundle_id,
        )
    except (AuthoritySelectionError, O3BundleError) as exc:
        # Fail closed: a requested-but-invalid O3 authority never degrades
        # into legacy answers, and an unknown selector is never guessed.
        parser.error(f"semantic authority selection failed: {exc}")
    print(
        "semantic authority: "
        f"{selection.provenance()}",
        file=sys.stderr,
    )
    # Cold-start corpus cache: a lazy snapshot-first hook on the shared
    # repository. Installing performs no I/O, so the stdio handshake never
    # blocks; the first listing of the bound revision is served from the
    # identity-bound snapshot when one exists, and a snapshot miss falls
    # back to the exact API load.
    corpus_cache.install_corpus_snapshot(service)
    create_mcp_server(service).run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
