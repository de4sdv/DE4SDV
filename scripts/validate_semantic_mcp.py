#!/usr/bin/env python3
"""Exercise all DE4SDV semantic MCP tools against one exact API binding."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.sysml_api.revisions import RevisionBinding

TOOL_NAMES = {
    "model_status",
    "resolve_element",
    "inspect_element",
    "semantic_neighbors",
    "impact",
    "trace",
    "verification_coverage",
}


def validate_semantic_results(
    results: dict[str, dict[str, Any]], *, expected_revision: dict[str, str]
) -> None:
    """Fail closed unless the MCP proof retains exact native semantics."""
    missing = TOOL_NAMES - results.keys()
    if missing:
        raise RuntimeError(f"MCP proof did not exercise tools: {sorted(missing)}")
    for name, result in results.items():
        if result.get("revision") != expected_revision:
            raise RuntimeError(
                f"{name} revision mismatch: {result.get('revision')} != {expected_revision}"
            )
    status = results["model_status"]
    if not status.get("current_baseline") or not status.get("read_only"):
        raise RuntimeError("model_status did not prove a read-only current baseline")
    impact_edges = results["impact"].get("edges", [])
    predicates = {edge.get("predicate") for edge in impact_edges}
    for required in ("hasSubject", "verifiedBy"):
        if required not in predicates:
            raise RuntimeError(f"full-model impact did not expose {required}")
    strengths = {edge.get("semantic_strength") for edge in impact_edges}
    if "native-reference" not in strengths or "native-verification" not in strengths:
        raise RuntimeError("full-model impact lost native semantic strengths")
    if not results["trace"].get("path"):
        raise RuntimeError("MCP semantic trace returned no ontology-mapped path")
    coverage = results["verification_coverage"]
    if coverage.get("status") not in {"covered", "partial"} or not coverage.get(
        "verification_cases"
    ):
        raise RuntimeError("MCP verification coverage did not resolve a case")
    if coverage.get("status") == "partial" and not coverage.get("gaps"):
        raise RuntimeError("partial verification coverage omitted its explicit gap")


def _structured(result: Any, tool_name: str) -> dict[str, Any]:
    if result.isError:
        raise RuntimeError(f"MCP tool {tool_name} failed: {result.content}")
    value = result.structuredContent
    if not isinstance(value, dict):
        raise RuntimeError(f"MCP tool {tool_name} returned no structured object")
    return value


async def run_mcp_validation(
    *,
    api_url: str,
    binding_path: Path,
    expected_git_revision: str,
    ontology_path: Path,
) -> dict[str, Any]:
    binding = RevisionBinding.load(binding_path)
    binding.require_current(expected_git_revision)
    if binding.scope != "full-model":
        raise RuntimeError(f"MCP proof requires full-model scope, got {binding.scope}")
    expected_revision = {
        "git_commit": binding.git_commit,
        "sysml_project_id": binding.sysml_project_id,
        "sysml_commit_id": binding.sysml_commit_id,
        "binding_status": "synchronized",
        "scope": "full-model",
    }
    params = StdioServerParameters(
        command=sys.executable,
        args=[
            str(ROOT / "scripts/semantic_mcp_server.py"),
            "--api-url",
            api_url,
            "--binding",
            str(binding_path),
            "--expected-git-revision",
            expected_git_revision,
            "--ontology",
            str(ontology_path),
        ],
        cwd=ROOT,
    )
    results: dict[str, dict[str, Any]] = {}
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            names = {tool.name for tool in listed.tools}
            if names != TOOL_NAMES:
                raise RuntimeError(
                    f"read-only MCP tool surface mismatch: {sorted(names)}"
                )
            for tool in listed.tools:
                annotations = tool.annotations
                if (
                    annotations is None
                    or not annotations.readOnlyHint
                    or annotations.destructiveHint
                    or not annotations.idempotentHint
                    or annotations.openWorldHint
                ):
                    raise RuntimeError(f"MCP tool {tool.name} is not strictly read-only")

            results["model_status"] = _structured(
                await session.call_tool("model_status", {}), "model_status"
            )
            results["resolve_element"] = _structured(
                await session.call_tool(
                    "resolve_element",
                    {"identifier": "reqCommandEmergencyBraking"},
                ),
                "resolve_element",
            )
            root_id = results["resolve_element"]["element"]["element_id"]
            results["inspect_element"] = _structured(
                await session.call_tool("inspect_element", {"identifier": root_id}),
                "inspect_element",
            )
            results["semantic_neighbors"] = _structured(
                await session.call_tool(
                    "semantic_neighbors", {"identifier": root_id}
                ),
                "semantic_neighbors",
            )
            results["impact"] = _structured(
                await session.call_tool(
                    "impact", {"identifier": "reqCommandEmergencyBraking"}
                ),
                "impact",
            )
            results["verification_coverage"] = _structured(
                await session.call_tool(
                    "verification_coverage",
                    {"requirement_identifier": root_id},
                ),
                "verification_coverage",
            )
            cases = results["verification_coverage"].get("verification_cases", [])
            if not cases:
                raise RuntimeError("no verification case available for MCP trace proof")
            results["trace"] = _structured(
                await session.call_tool(
                    "trace",
                    {
                        "source_identifier": root_id,
                        "target_identifier": cases[0]["element_id"],
                        "max_depth": 4,
                    },
                ),
                "trace",
            )

    validate_semantic_results(results, expected_revision=expected_revision)
    return {
        "schema": "de4sdv-semantic-mcp-validation/v1",
        "read_only": True,
        "revision": expected_revision,
        "tool_count": len(results),
        "tools": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--expected-git-revision", required=True)
    parser.add_argument(
        "--ontology",
        type=Path,
        default=ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = anyio.run(
        lambda: run_mcp_validation(
            api_url=args.api_url,
            binding_path=args.binding,
            expected_git_revision=args.expected_git_revision,
            ontology_path=args.ontology,
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "read_only": result["read_only"],
                "tool_count": result["tool_count"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
