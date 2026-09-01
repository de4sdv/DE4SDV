"""Thin read-only MCP protocol adapter for DE4SDV semantic queries.

Engineering semantics live in :mod:`de4sdv.semantic.query`, the ontology, and
native traversal strategies. This module only declares an MCP tool surface.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .query import SemanticQueryService

_READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)


def create_mcp_server(service: SemanticQueryService) -> FastMCP:
    """Create an agent-independent MCP server over one semantic service."""
    mcp = FastMCP(
        "DE4SDV Semantic Queries",
        instructions=(
            "Read-only, revision-bound SysML v2 semantic queries. Results use "
            "ontology-declared mappings and preserve UUID/revision provenance."
        ),
    )

    @mcp.tool(annotations=_READ_ONLY, structured_output=True)
    def model_status() -> dict[str, Any]:
        """Report exact Git/SysML binding status and read-only runtime scope."""
        return service.model_status()

    @mcp.tool(annotations=_READ_ONLY, structured_output=True)
    def resolve_element(
        identifier: str, expected_type: str | None = None
    ) -> dict[str, Any]:
        """Resolve one exact API identity, failing closed on ambiguity."""
        return service.resolve_element(identifier, expected_type=expected_type)

    @mcp.tool(annotations=_READ_ONLY, structured_output=True)
    def inspect_element(identifier: str) -> dict[str, Any]:
        """Inspect one semantically resolved element without dumping the model."""
        return service.inspect_element(identifier)

    @mcp.tool(annotations=_READ_ONLY, structured_output=True)
    def semantic_neighbors(
        identifier: str, predicates: list[str] | None = None
    ) -> dict[str, Any]:
        """Return compact neighbors from ontology-declared semantic mappings."""
        return service.semantic_neighbors(identifier, predicates=predicates)

    @mcp.tool(annotations=_READ_ONLY, structured_output=True)
    def impact(identifier: str) -> dict[str, Any]:
        """Return revision-bound requirement impact with strengths and gaps."""
        return service.impact(identifier)

    @mcp.tool(annotations=_READ_ONLY, structured_output=True)
    def trace(
        source_identifier: str, target_identifier: str, max_depth: int = 4
    ) -> dict[str, Any]:
        """Find a bounded path using only ontology-declared semantic mappings."""
        return service.trace(
            source_identifier, target_identifier, max_depth=max_depth
        )

    @mcp.tool(annotations=_READ_ONLY, structured_output=True)
    def verification_coverage(requirement_identifier: str) -> dict[str, Any]:
        """Report API-backed verification cases or explicit verification gaps."""
        return service.verification_coverage(requirement_identifier)

    return mcp
