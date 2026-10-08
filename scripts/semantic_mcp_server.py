#!/usr/bin/env python3
"""Run the read-only DE4SDV semantic MCP server over stdio.

Semantic authority is selected explicitly (O4 Wave C2: model only):

    --semantic-authority model             DE4SDV_SEMANTIC_AUTHORITY
    --model-authority-bundle <path>        DE4SDV_MODEL_AUTHORITY_BUNDLE
    --model-authority-bundle-id <mab-...>  DE4SDV_MODEL_AUTHORITY_BUNDLE_ID

There is no default: an unset selector, the retired values ``legacy`` and
``o3`` and any unknown value refuse to start. The model request is verified
at startup (exact revision, revision binding v2, closed bundle attestation,
activation eligibility); any failure refuses to start. Procedure:
docs/method-conformance/o4/model-authority-activation.md.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.authority_selection import (  # noqa: E402
    AuthoritySelectionError,
)
from de4sdv.semantic.entry_authority import (  # noqa: E402
    build_entry_semantic_runtime as build_selected_semantic_runtime,
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
    parser.add_argument(
        "--semantic-authority",
        help="explicit semantic authority: model (the only accepted value; "
             "default DE4SDV_SEMANTIC_AUTHORITY, unset is refused)",
    )
    parser.add_argument(
        "--model-authority-bundle",
        help="path to the accepted model-authority bundle JSON (model)",
    )
    parser.add_argument(
        "--model-authority-bundle-id",
        help="exact accepted model-authority bundle id (mab-...)",
    )
    parser.add_argument(
        "--allow-candidate-bundle",
        action="store_true",
        help="serve an unclosed candidate bundle (privileged evidence validation only; "
             "never a production setting)",
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
            api_timeout=args.api_timeout,
            authority=args.semantic_authority,
            model_bundle_path=args.model_authority_bundle,
            model_bundle_id=args.model_authority_bundle_id,
            **({"require_activation_eligible": False} if args.allow_candidate_bundle else {}),
        )
    except AuthoritySelectionError as exc:
        # Fail closed: an unset, retired or unknown selector is refused and a
        # requested model authority never degrades into another authority.
        parser.error(f"semantic authority selection failed: {exc}")
    print(
        "semantic authority: "
        f"{selection.provenance()}",
        file=sys.stderr,
    )
    create_mcp_server(service).run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
