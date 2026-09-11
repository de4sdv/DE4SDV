"""Surface-gate regressions for scripts/validate_semantic_mcp.py.

Post-Lane-C integration defect: the validator required exact equality with the
seven full-model semantic proof tools, so the privileged ingestion failed
merely because four additive strictly read-only method-conformance tools
existed. The gate is now a required-subset contract:

* every required semantic proof tool must be present (missing ones fail
  closed);
* additive strictly read-only tools are allowed;
* EVERY exposed tool - required or additive - must satisfy the strict
  read-only annotations (readOnlyHint true, destructiveHint false,
  idempotentHint true, openWorldHint false).

These tests exercise the pure surface-validation helper; no API is required.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.validate_semantic_mcp import (
    REQUIRED_SEMANTIC_PROOF_TOOLS,
    validate_tool_surface,
)

#: Lane C additive, strictly read-only method-conformance tools.
LANE_C_TOOLS = (
    "phase_contract",
    "increment_status",
    "method_gaps",
    "next_obligation",
)


def tool(
    name: str,
    *,
    read_only: bool = True,
    destructive: bool = False,
    idempotent: bool = True,
    open_world: bool = False,
) -> SimpleNamespace:
    """A minimal stand-in for an MCP listed tool with strict annotations."""
    return SimpleNamespace(
        name=name,
        annotations=SimpleNamespace(
            readOnlyHint=read_only,
            destructiveHint=destructive,
            idempotentHint=idempotent,
            openWorldHint=open_world,
        ),
    )


def required_tools() -> list[SimpleNamespace]:
    return [tool(name) for name in sorted(REQUIRED_SEMANTIC_PROOF_TOOLS)]


# ---------------------------------------------------------------------------
# 1. exactly the original seven tools passes
# ---------------------------------------------------------------------------


def test_required_seven_tools_pass() -> None:
    counts = validate_tool_surface(required_tools())
    assert counts == {"exposed_tool_count": 7, "required_tool_count": 7}


# ---------------------------------------------------------------------------
# 2. seven required + the four Lane C read-only tools passes
# ---------------------------------------------------------------------------


def test_seven_required_plus_lane_c_read_only_tools_pass() -> None:
    tools = required_tools() + [tool(name) for name in LANE_C_TOOLS]
    counts = validate_tool_surface(tools)
    assert counts == {"exposed_tool_count": 11, "required_tool_count": 7}


# ---------------------------------------------------------------------------
# 3. missing any required proof tool fails
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("missing", sorted(REQUIRED_SEMANTIC_PROOF_TOOLS))
def test_missing_required_proof_tool_fails(missing: str) -> None:
    tools = [t for t in required_tools() if t.name != missing]
    with pytest.raises(RuntimeError, match="missing required semantic proof tools"):
        validate_tool_surface(tools)


def test_missing_required_tool_fails_even_with_additive_tools_present() -> None:
    tools = [
        t for t in required_tools() if t.name != "verification_coverage"
    ] + [tool(name) for name in LANE_C_TOOLS]
    with pytest.raises(RuntimeError, match="verification_coverage"):
        validate_tool_surface(tools)


# ---------------------------------------------------------------------------
# 4-6. additive tools must still be strictly read-only
# ---------------------------------------------------------------------------


def test_additive_tool_with_non_read_only_annotation_fails() -> None:
    tools = required_tools() + [tool("phase_contract", read_only=False)]
    with pytest.raises(RuntimeError, match="phase_contract.*not strictly read-only"):
        validate_tool_surface(tools)


def test_additive_destructive_tool_fails() -> None:
    tools = required_tools() + [tool("increment_status", destructive=True)]
    with pytest.raises(RuntimeError, match="increment_status.*not strictly read-only"):
        validate_tool_surface(tools)


def test_additive_open_world_tool_fails() -> None:
    tools = required_tools() + [tool("method_gaps", open_world=True)]
    with pytest.raises(RuntimeError, match="method_gaps.*not strictly read-only"):
        validate_tool_surface(tools)


def test_additive_non_idempotent_tool_fails() -> None:
    tools = required_tools() + [tool("next_obligation", idempotent=False)]
    with pytest.raises(RuntimeError, match="next_obligation.*not strictly read-only"):
        validate_tool_surface(tools)


def test_required_tool_with_non_read_only_annotation_still_fails() -> None:
    """All required tools present is not enough: each must be read-only."""
    tools = [
        tool(name, destructive=True) if name == "trace" else tool(name)
        for name in sorted(REQUIRED_SEMANTIC_PROOF_TOOLS)
    ]
    with pytest.raises(RuntimeError, match="trace.*not strictly read-only"):
        validate_tool_surface(tools)


def test_tool_without_annotations_fails() -> None:
    tools = required_tools() + [SimpleNamespace(name="bare_tool", annotations=None)]
    with pytest.raises(RuntimeError, match="bare_tool.*not strictly read-only"):
        validate_tool_surface(tools)


# ---------------------------------------------------------------------------
# The real declared server surface satisfies the required-subset gate
# ---------------------------------------------------------------------------


def test_declared_server_surface_satisfies_required_subset() -> None:
    """The live declared surface passes the gate with all eleven tools.

    Registration never touches the service, so a stub is sufficient; the
    exercised semantic proof itself is covered by tests/test_semantic_mcp.py
    and the privileged ingestion.
    """

    from de4sdv.semantic.mcp_server import create_mcp_server

    class _StubService:
        """Registration-only stub: no tool is called in this test."""

    server = create_mcp_server(_StubService())  # type: ignore[arg-type]
    listed = server._tool_manager.list_tools()

    counts = validate_tool_surface(listed)
    assert counts == {"exposed_tool_count": 11, "required_tool_count": 7}
    names = {listed_tool.name for listed_tool in listed}
    assert REQUIRED_SEMANTIC_PROOF_TOOLS <= names
    assert set(LANE_C_TOOLS) <= names
