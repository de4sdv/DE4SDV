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
            "ontology-declared mappings and preserve UUID/revision provenance. "
            "An identifier is an element UUID, a declared short name, an exact "
            "qualified name such as DE4SDV_MethodContext::EngineeringIncrement (element "
            "names along ownership), or a unique bare name; inspect_element describes a "
            "definition's features. "
            "The method tools evaluate the bound revision only and state what "
            "they cover: a workflow phase without executable checks is reported, "
            "never evaluated, and an increment the revision does not declare is "
            "answered as such (work on a branch is evaluated by the PR Method Check)."
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
        """Resolve one exact API identity, failing closed on ambiguity. `identifier` is a UUID, a
        declared short name (`INC-AEBS-010`), a qualified name (`DE4SDV_MethodContext::EngineeringIncrement`,
        as phase_contract and the Method Check print it; matched by every segment, never by a bare name)
        or a unique bare name. A qualified name resolves only through element names along ownership: a path
        through a short name, an alias, an inherited or an imported member is refused, and the refusal gives
        the canonical qualified name, or every one when the name reaches several elements (ambiguous there).
        The explanation follows one import level and inheritance through authored specializations only.
        An identity that is not found names the revision it searched."""
        return service.resolve_element(identifier, expected_type=expected_type)

    @mcp.tool(annotations=_READ_ONLY, structured_output=True)
    def inspect_element(identifier: str) -> dict[str, Any]:
        """Inspect one element without dumping the model; `identifier` as for resolve_element, for example
        a qualified name (element names along ownership only; a short name, an alias, an inherited or an
        imported member is refused with the canonical qualified name, or every one when the name is
        ambiguous; one import level and authored specializations are followed). Returns its qualified name,
        `keyword`, owning package and documentation. For a definition, `element.definition` adds its
        supertypes, its owned and inherited features (name, keyword, type as a qualified name,
        multiplicity, value; `type_outside_export` when the type is not in the export) and an enumeration
        definition's enumerated values."""
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

    # ------------------------------------------------------------------
    # Method surfaces: one increment against the model's method gates
    # (frozen baseline Section 13). ``increment`` is the registered
    # identifier carried as the increment usage's declared short name;
    # ``phase`` (a MethodPhase literal) optionally filters the projection.
    # Every answer evaluates the bound revision only and says what it
    # covers (docs/guides/drive-an-increment-with-the-method-tools.md).
    # ------------------------------------------------------------------

    @mcp.tool(annotations=_READ_ONLY, structured_output=True)
    def phase_contract(phase: str | None = None, increment: str | None = None) -> dict[str, Any]:
        """Return the method of the bound revision (optionally one phase): every workflow step with its
        declared inputs and outputs (`steps`; one with coverage "no executable checks at this revision" is
        never evaluated) and the executable checks (`gates`). Per gate, `population` bounds the number of
        subjects (the multiplicity of the step parameter) and `cardinality` the distinct targets each subject
        must reach. With an increment, also whether each step and gate applies to it, and per gate
        `what_satisfies` and `authoring`: SysML built from the step parameter the check is about
        (`parameter_element_id`), with qualified type names and the `private import` lines they need; in
        `authoring`, `phases` lists the MethodPhase literals for the applicable-phases check. No verdict.
        A `subject_type` containing `::` names a definition: pass it, or a parameter `type`, to inspect_element.
        A `subject_type` without `::` is the SysML metaclass of an untyped parameter, not a model element
        (`subject_type_kind` is `metaclass`); its subject is declared by its `subject_keyword`."""
        return service.phase_contract(phase, increment=increment)

    @mcp.tool(annotations=_READ_ONLY, structured_output=True)
    def increment_status(increment: str, phase: str | None = None) -> dict[str, Any]:
        """Per-phase status of one increment at the bound revision: aggregate verdict and phase-exit
        readiness of the executable checks. A declared phase without executable checks is listed with
        its step's declared outputs, never evaluated. Such a phase's exit is BLOCKED by the method
        (CONTRACT_UNAVAILABLE), never by a gap. A declared phase whose blocking checks are all not
        applicable is READY and marked `vacuous: true`, with `evaluated` (advisory checks evaluated);
        readiness stays READY or BLOCKED. `coverage` names the phases the verdicts cover. If the
        revision does not declare the increment, `increment.resolution` is `not-declared`."""
        return service.increment_status(phase, increment=increment)

    @mcp.tool(annotations=_READ_ONLY, structured_output=True)
    def method_gaps(increment: str, phase: str | None = None) -> dict[str, Any]:
        """Unmet blocking gates of one increment at the bound revision, with subjects and what to author,
        plus advisory notes. `what_to_author` and `authoring` give the SysML to write, built from the step
        parameter the check is about: qualified type names, the `private import` lines and the order of
        declarations (`phases`: the MethodPhase literals, for the applicable-phases check). Only phases
        with executable checks have gates: an empty list says nothing about the
        declared phases `coverage` lists without executable checks."""
        return service.method_gaps(phase, increment=increment)

    @mcp.tool(annotations=_READ_ONLY, structured_output=True)
    def next_obligation(increment: str, phase: str | None = None) -> dict[str, Any]:
        """The first actionable gate of one increment at the bound revision, in workflow order (step order,
        then check order), with what to author (`authoring`: declarations with qualified type names, their
        `private import` lines, types, notes and, for the applicable-phases check, the MethodPhase literals
        in `phases`) and where. `reason` always says why. `vacuous_phases` lists the vacuous phases before
        `next` (within `phase`), each with a review `prompt`: advisory, it never blocks, never changes
        `next` and needs no model record to clear. When
        `increment.resolution` is `not-declared`, the bound revision does not declare the increment: work
        on a branch is evaluated by the PR Method Check, not by this revision."""
        return service.next_obligation(phase, increment=increment)

    return mcp
