#!/usr/bin/env python3
"""Exercise the required DE4SDV semantic MCP proof tools against one exact API binding.

The privileged full-model proof calls the seven required semantic proof tools.
The surface gate is a required-subset contract: every required proof tool must
be present (missing ones fail closed), additive strictly read-only tools are
allowed, and *every* exposed MCP tool - required or additive - must satisfy
the strict read-only annotations. Additive tools are counted, never called by
this proof; only the required seven are exercised.

c5 integration closure (PR #249, R1+R2): the proof establishes two
INDEPENDENT facts and fails closed unless both hold.

Proof A - blocked EvidenceContract state: ``hasRelevantEvidenceContract`` is
governed blocked at the reviewed revision (EvidenceContract-specific identity
is not machine-resolvable; native verification membership also admits
``AcceptanceCriterion``). The proof asserts the blocked/unsupported state is
exposed (not ordinary absence), that zero EvidenceContract edges are emitted,
and that verification coverage is reported as incomplete - never as ordinary
``uncovered`` with an empty explanation - while the range is blocked.

Proof B - native verification still works: ``verifiedBy`` is an independently
reviewed native ``Requirement -> VerificationCase`` relation grounded in
``RequirementVerificationMembership``; its proof never depends on the blocked
EvidenceContract route. The subject is selected from native API membership
facts (never from names or layout) and must satisfy the relation's declared
source domain: the anchored usage resolves to a governed DE4SDV Requirement
identity, either by direct Requirement-lineage grounding or through the
reviewed ReferenceSubsetting shadow bridge (c5 R2 verifiedBy-domain
consistency review). The proof exercises a real verification case through
the supported query surfaces with ``native-verification`` semantic strength
and exact revision provenance. The hasSubject / native-reference subject
surface stays asserted on the PROOF-A requirement: on the retained model no
natively verified requirement usage carries a member-product subject hop,
while requirements without native verification do (measured; see the c5
review Section 17.2), so demanding that surface from the Proof-B subject
would demand a fact the declared semantics never placed there.

"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.kernel_binding_index import KernelBindingIndex
from de4sdv.semantic.kernel_contract import KernelContract
from de4sdv.semantic.relationships import build_relationship_graph
from de4sdv.semantic.traversal import SemanticTraversal
from de4sdv.sysml_api.client import ApiClient
from de4sdv.sysml_api.repository import SysMLRepository, element_id, reference_ids
from de4sdv.sysml_api.revisions import RevisionBinding

#: The seven full-model semantic proof tools this validator exercises. The
#: exposed surface may be larger (strictly read-only additions are allowed);
#: these are the tools whose results carry the semantic proof.
REQUIRED_SEMANTIC_PROOF_TOOLS = {
    "model_status",
    "resolve_element",
    "inspect_element",
    "semantic_neighbors",
    "impact",
    "trace",
    "verification_coverage",
}

#: Reviewed discriminators that establish the governed DE4SDV ``Requirement``
#: identity of a Proof-B subject (c5 R2 verifiedBy-domain consistency
#: review): direct Requirement-lineage grounding of the anchored usage, or
#: the reviewed ReferenceSubsetting shadow bridge followed by the same
#: grounding proof on the declared usage. Both are machine-resolvable,
#: deterministic, revision-bound, and fail closed; names, packages, and
#: source text never participate.
REQUIREMENT_IDENTITY_BASES = (
    "direct-requirement-lineage",
    "reference-subsetting-shadow",
)


def validate_tool_surface(tools: Iterable[Any]) -> dict[str, int]:
    """Fail closed unless the exposed MCP surface is complete and safe.

    Required-subset semantics: every required semantic proof tool must be
    present; additive tools are allowed. Every exposed tool - required or
    additive - must satisfy the strict read-only annotations (readOnlyHint
    true, destructiveHint false, idempotentHint true, openWorldHint false).
    Destructive or open-world tools are refused even when all required tools
    are present.

    Returns the distinct counts for output clarity: ``exposed_tool_count``
    (everything on the surface) and ``required_tool_count`` (the proof set).
    """
    exposed: dict[str, Any] = {}
    for tool in tools:
        name = str(getattr(tool, "name", "") or "")
        if not name:
            raise RuntimeError("MCP surface exposed a tool without a name")
        exposed[name] = tool

    missing = REQUIRED_SEMANTIC_PROOF_TOOLS - exposed.keys()
    if missing:
        raise RuntimeError(
            "read-only MCP surface is missing required semantic proof tools: "
            f"{sorted(missing)}"
        )

    for name in sorted(exposed):
        annotations = getattr(exposed[name], "annotations", None)
        if (
            annotations is None
            or not annotations.readOnlyHint
            or annotations.destructiveHint
            or not annotations.idempotentHint
            or annotations.openWorldHint
        ):
            raise RuntimeError(f"MCP tool {name} is not strictly read-only")

    return {
        "exposed_tool_count": len(exposed),
        "required_tool_count": len(REQUIRED_SEMANTIC_PROOF_TOOLS),
    }


def _require_blocked_evidence_state(
    neighbors: dict[str, Any], coverage: dict[str, Any]
) -> None:
    """Proof A: the governed blocked EvidenceContract state must be exposed.

    Both results must belong to the SAME Proof-A requirement: the coverage
    subject must be the neighbor root. Fails closed if the blocked state
    disappears unexpectedly, if any false EvidenceContract edge is emitted,
    or if Proof-A results drift onto different subjects. Blocked semantic
    authority is distinct from zero supported matches: the results must say
    so explicitly.
    """
    root_id = (neighbors.get("root") or {}).get("element_id")
    coverage_subject = (coverage.get("requirement") or {}).get("element_id")
    if not root_id or not coverage_subject:
        raise RuntimeError(
            "Proof A results do not expose their requirement identities"
        )
    if root_id != coverage_subject:
        raise RuntimeError(
            "Proof A is not subject-coherent: semantic_neighbors root "
            f"{root_id} != verification_coverage requirement {coverage_subject}"
        )
    unsupported = neighbors.get("unsupported_predicates")
    if not isinstance(unsupported, list) or not any(
        isinstance(item, dict)
        and item.get("predicate") == "hasRelevantEvidenceContract"
        and item.get("authority_state") == "blocked"
        and "EvidenceContract-specific identity is not machine-resolvable"
        in str(item.get("reason", ""))
        for item in unsupported
    ):
        raise RuntimeError(
            "semantic_neighbors did not expose the governed blocked "
            "hasRelevantEvidenceContract state (blocked != ordinary absence)"
        )
    if neighbors.get("semantic_status") != "incomplete":
        raise RuntimeError(
            "semantic_neighbors reported a complete evaluation while the "
            "EvidenceContract range is blocked"
        )
    blocked_edges = [
        edge
        for edge in neighbors.get("edges", [])
        if edge.get("predicate") == "hasRelevantEvidenceContract"
    ]
    if blocked_edges:
        raise RuntimeError(
            "false EvidenceContract edges were emitted while the range is "
            f"blocked: {len(blocked_edges)}"
        )
    if coverage.get("status") not in {"incomplete", "partial"}:
        raise RuntimeError(
            "verification_coverage must not report plain 'uncovered' while "
            "the EvidenceContract range is blocked; the blocked range makes "
            f"the assessment incomplete or partial, got {coverage.get('status')!r}"
        )
    if coverage.get("semantic_status") != "incomplete":
        raise RuntimeError(
            "verification_coverage reported a complete semantic evaluation "
            "while the EvidenceContract range is blocked"
        )
    if not any(
        isinstance(item, dict)
        and item.get("predicate") == "hasRelevantEvidenceContract"
        for item in coverage.get("unsupported_predicates", [])
    ):
        raise RuntimeError(
            "verification_coverage lost the blocked EvidenceContract "
            "unsupported-predicate record"
        )
    if not any(
        gap.get("category") == "verification-unsupported"
        and "EvidenceContract" in str(gap.get("reason", ""))
        for gap in coverage.get("gaps", [])
    ):
        raise RuntimeError(
            "verification_coverage omitted the blocked-range explanation"
        )
    if coverage.get("evidence_contracts"):
        raise RuntimeError(
            "false EvidenceContract claims present in verification_coverage "
            "while the range is blocked"
        )


def _require_native_verification_proof(
    impact: dict[str, Any], coverage: dict[str, Any], trace: dict[str, Any]
) -> None:
    """Proof B: native ``verifiedBy`` is proven independently of EvidenceContract.

    All three results must belong to the SAME selected native-verification
    subject: the impact root, the coverage requirement, and the trace source
    must be one coherent Requirement (c5 integration-closure correction,
    PR #249). Proof B never consumes another requirement's coverage. The
    proof requires a real native verification relationship
    (``native-verification`` strength), a real VerificationCase node, and a
    meaningful trace over the supported native relation - never a result that
    depended on the blocked EvidenceContract route.
    """
    impact_root = (impact.get("root") or {}).get("element_id")
    coverage_subject = (coverage.get("requirement") or {}).get("element_id")
    trace_source = (trace.get("source") or {}).get("element_id")
    if not impact_root or not coverage_subject or not trace_source:
        raise RuntimeError(
            "Proof B results do not expose their requirement identities"
        )
    if not (impact_root == coverage_subject == trace_source):
        raise RuntimeError(
            "Proof B is not subject-coherent: impact root "
            f"{impact_root}, coverage requirement {coverage_subject}, trace "
            f"source {trace_source} must all be the selected native "
            "verification subject"
        )
    impact_edges = impact.get("edges", [])
    verification_edges = [
        edge for edge in impact_edges if edge.get("predicate") == "verifiedBy"
    ]
    if not verification_edges:
        raise RuntimeError("native verifiedBy was not exposed in impact")
    strengths = {edge.get("semantic_strength") for edge in impact_edges}
    if "native-verification" not in strengths:
        raise RuntimeError("native-verification semantic strength was lost")
    if any(
        edge.get("semantic_strength") != "native-verification"
        for edge in verification_edges
    ):
        raise RuntimeError("verifiedBy edges carry a non-native strength")
    case_ids = {
        edge.get("target")
        for edge in verification_edges
        if edge.get("target")
    }
    if not case_ids:
        raise RuntimeError("verifiedBy edges resolved to no verification case")
    node_ids = {
        node.get("element_id")
        for node in impact.get("nodes", [])
        if node.get("element_id")
    }
    if not case_ids <= node_ids:
        raise RuntimeError("verifiedBy targets are not backed by impact nodes")
    if coverage.get("status") not in {"covered", "partial"}:
        raise RuntimeError(
            "verification_coverage did not report a resolvable native case "
            f"(got {coverage.get('status')!r})"
        )
    reported_cases = coverage.get("verification_cases") or []
    if not any(
        case.get("element_id") in case_ids for case in reported_cases
    ):
        raise RuntimeError(
            "verification_coverage did not retain the proven native case"
        )
    trace_path = trace.get("path") or []
    if not trace_path:
        raise RuntimeError("MCP semantic trace returned no ontology-mapped path")
    trace_predicates = {step.get("predicate") for step in trace_path}
    if "verifiedBy" not in trace_predicates:
        raise RuntimeError("trace proof no longer exercises native verifiedBy")


def _require_proof_b_subject_identity(
    proof_b_subject: dict[str, Any] | None, proof_b_impact: dict[str, Any]
) -> None:
    """Explicit source-domain assertion for the Proof-B subject.

    The declared ``verifiedBy`` predicate is ``Requirement ->
    VerificationCase``; the production subject selection can only return a
    usage whose governed DE4SDV Requirement identity is machine-proven
    (direct Requirement-lineage grounding, or the reviewed
    ReferenceSubsetting shadow bridge — c5 R2 verifiedBy-domain consistency
    review). When the production path supplies the subject record, this
    assertion makes that enforcement part of the validated proof: the record
    must carry the reviewed identity evidence and must be the exact
    requirement the Proof-B triple was evaluated on. The same-subject
    fallback shapes (tests) may omit the record.
    """
    if proof_b_subject is None:
        return
    subject_id = proof_b_subject.get("element_id")
    if not subject_id:
        raise RuntimeError(
            "Proof B subject record does not carry its requirement identity"
        )
    identity = proof_b_subject.get("requirement_identity")
    if not isinstance(identity, dict):
        raise RuntimeError(
            "Proof B subject does not satisfy the verifiedBy source domain: "
            "no machine-proven governed DE4SDV Requirement identity is recorded"
        )
    if identity.get("basis") not in REQUIREMENT_IDENTITY_BASES:
        raise RuntimeError(
            "Proof B subject requirement-identity basis is not one of the "
            f"reviewed discriminators: {identity.get('basis')!r}"
        )
    if not identity.get("requirement_lineage_root_id"):
        raise RuntimeError(
            "Proof B subject requirement identity lacks its validated lineage root"
        )
    impact_root = (proof_b_impact.get("root") or {}).get("element_id")
    if subject_id != impact_root:
        raise RuntimeError(
            "Proof B subject does not match the proof triple: subject "
            f"{subject_id} != impact root {impact_root}"
        )


def validate_semantic_results(
    results: dict[str, dict[str, Any]],
    *,
    expected_revision: dict[str, Any],
    proof_b_impact: dict[str, Any] | None = None,
    proof_b_coverage: dict[str, Any] | None = None,
    proof_b_trace: dict[str, Any] | None = None,
    proof_b_subject: dict[str, Any] | None = None,
    require_subject_edge: bool = True,
) -> None:
    """Fail closed unless the MCP proof retains exact native semantics.

    The two-proof architecture (c5 integration closure, PR #249): Proof A is
    anchored on the EvidenceContract-review requirement (neighbors +
    coverage); Proof B is anchored on the independently selected native
    verification subject. When explicit Proof-B results are provided they
    are validated as the native-verification proof and must NOT be the
    Proof-A objects (the Proof-B subject is allowed — and on the retained
    model expected — to differ from the Proof-A root). Without explicit
    Proof-B results the single-subject shapes are accepted, in which case
    Proof A and Proof B happen to share one requirement.

    Proof-B source domain (c5 R2 verifiedBy-domain consistency review): the
    declared predicate is ``Requirement -> VerificationCase``; when the
    production path supplies ``proof_b_subject``, the proof must carry the
    machine-proven Requirement identity of the selected subject. The
    hasSubject / native-reference subject surface is asserted on the PROOF-A
    surface (``semantic_neighbors``): on the retained model no natively
    verified requirement usage carries a member-product subject hop, while
    the Proof-A requirement does — the surface belongs where the model
    actually carries it.
    """
    missing = REQUIRED_SEMANTIC_PROOF_TOOLS - results.keys()
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
    # Proof A: blocked EvidenceContract state is explicit, zero false edges.
    proof_a_neighbors = results["semantic_neighbors"]
    proof_a_coverage = results["verification_coverage"]
    _require_blocked_evidence_state(proof_a_neighbors, proof_a_coverage)
    # Proof B: native verification on the selected subject — either the
    # explicit two-subject results or the same-subject fallback. The
    # explicit subject record carries the enforced source-domain proof.
    proof_b_impact = (
        proof_b_impact if proof_b_impact is not None else results["impact"]
    )
    proof_b_coverage = (
        proof_b_coverage
        if proof_b_coverage is not None
        else results["verification_coverage"]
    )
    proof_b_trace = proof_b_trace if proof_b_trace is not None else results["trace"]
    for name, result in (
        ("proof_b_impact", proof_b_impact),
        ("proof_b_coverage", proof_b_coverage),
        ("proof_b_trace", proof_b_trace),
    ):
        if result.get("revision") != expected_revision:
            raise RuntimeError(
                f"{name} revision mismatch: {result.get('revision')} != {expected_revision}"
            )
    _require_native_verification_proof(
        proof_b_impact, proof_b_coverage, proof_b_trace
    )
    _require_proof_b_subject_identity(proof_b_subject, proof_b_impact)
    proof_a_edges = proof_a_neighbors.get("edges", [])
    if require_subject_edge and not any(
        edge.get("predicate") == "hasSubject" for edge in proof_a_edges
    ):
        raise RuntimeError("full-model Proof-A surface did not expose hasSubject")
    proof_a_strengths = {edge.get("semantic_strength") for edge in proof_a_edges}
    if require_subject_edge and "native-reference" not in proof_a_strengths:
        raise RuntimeError(
            "full-model Proof-A surface lost native-reference strength"
        )


def _structured(result: Any, tool_name: str) -> dict[str, Any]:
    if result.isError:
        raise RuntimeError(f"MCP tool {tool_name} failed: {result.content}")
    value = result.structuredContent
    if not isinstance(value, dict):
        raise RuntimeError(f"MCP tool {tool_name} returned no structured object")
    return value


def _reference_subsetting_bridge(
    elements: list[dict[str, Any]],
) -> dict[str, list[str]]:
    """Serialized shadow -> declared usage bridge (the reviewed c2 mechanism).

    A ``verify`` statement can serialize as an RVM whose member is a
    reference-usage shadow rather than the declared requirement usage; the
    bridge is the owned ``ReferenceSubsetting`` whose ``referencedFeature``
    is the declared original. Same serializer keys the reviewed verifiedBy
    resolver consumes; declared targets keep element order (deterministic)
    and are deduplicated. Nothing here establishes identity: the caller
    still grounds the declared usage in the validated Requirement lineage
    and fails closed otherwise.
    """
    bridge: dict[str, list[str]] = {}
    for element in elements:
        if str(element.get("@type")) != "ReferenceSubsetting":
            continue
        declared_ids = reference_ids(element.get("referencedFeature"))
        shadow_ids = reference_ids(element.get("owningRelatedElement")) + (
            reference_ids(element.get("owner"))
        )
        for declared in declared_ids:
            for shadow in shadow_ids:
                targets = bridge.setdefault(shadow, [])
                if declared not in targets:
                    targets.append(declared)
    return bridge


def _requirement_identity(
    anchor: dict[str, Any],
    resolver: dict[str, Any],
    bridge: dict[str, list[str]],
    by_id: dict[str, dict[str, Any]],
    traversal: Any,
) -> tuple[str, str, str] | None:
    """Machine-prove the governed DE4SDV Requirement identity of one anchor.

    Returns ``(subject_id, basis, grounding_provenance)`` when the identity
    is established, ``None`` otherwise (fail closed; the caller never falls
    back to API metaclass, name, package, or source text):

    - ``direct-requirement-lineage``: the anchored usage itself grounds in
      the validated Requirement-lineage closure (authored or tool-implied
      specialization/typing provenance, per the reviewed grounding
      machinery);
    - ``reference-subsetting-shadow``: the anchor is a serialized shadow
      reference usage and its declared usage (the reviewed
      ReferenceSubsetting bridge, c2 Section 2.2) grounds in that lineage.

    Both discriminators are machine-resolvable, deterministic,
    revision-bound, and testable; ``grounding_provenance`` is the reviewed
    endpoint-grounding provenance (``explicit`` / ``implied``).
    """
    anchor_id = element_id(anchor)
    if anchor_id is None:
        return None
    grounding = traversal._endpoint_grounding(anchor, resolver)
    if grounding is not None:
        return anchor_id, "direct-requirement-lineage", grounding
    for declared_id in bridge.get(anchor_id, ()):  # element order
        declared = by_id.get(declared_id)
        if declared is None or str(declared.get("@type")) != "RequirementUsage":
            continue
        declared_grounding = traversal._endpoint_grounding(declared, resolver)
        if declared_grounding is not None:
            return declared_id, "reference-subsetting-shadow", declared_grounding
    return None


def _select_native_verification_subject(
    elements: list[dict[str, Any]], traversal: Any
) -> dict[str, Any]:
    """Select the Proof-B subject from native membership facts only.

    The subject must satisfy BOTH conditions (c5 R2 verifiedBy-domain
    consistency review):

    1. governed DE4SDV Requirement identity (the declared ``verifiedBy``
       source domain): the anchored usage grounds in the validated
       Requirement lineage directly, or is a serialized ReferenceSubsetting
       shadow whose declared usage grounds in that lineage (the reviewed c2
       bridge — the same serializer keys the verifiedBy resolver consumes);
       and
    2. a native verification case resolvable through the reviewed owner-chain
       ``verifiedBy`` resolver itself (``traversal.traverse("verifiedBy", …)``
       on the PROVEN subject).

    Fails closed on anything else: an ungrounded ``RequirementUsage`` (a bare
    API ``@type`` never establishes identity), a Need-role usage (sibling
    lineage), an acceptance-criterion-shaped usage outside the Requirement
    lineage, or a proven subject whose case does not resolve. No name,
    package, file, or source-text heuristic participates; anchor enumeration
    order is the export's deterministic order.

    The previous revision deliberately carried NO lineage condition based on
    the finding that all 64 direct RVM anchors lie outside the
    Requirement/Need/AcceptanceCriterion lineages. Re-measurement showed
    that finding holds for the direct anchor alone: resolved through the
    reviewed shadow bridge — the anchored usage, per the reviewed c2
    semantics — 30 of the 64 anchored usages ground explicitly in the
    Requirement lineage (all acceptance-criterion-role usages), while 34
    remain unresolved (evidence-contract-role usages whose definitions
    carry no lineage) and must fail closed. The declared domain is therefore
    enforceable and is enforced here; the claim for the subject's DE4SDV
    class identity is now backed by proof instead of being skipped.
    """
    by_id: dict[str, dict[str, Any]] = {}
    for item in elements:
        candidate_id = element_id(item)
        if candidate_id is not None:
            by_id[candidate_id] = item

    anchors: list[tuple[str, dict[str, Any]]] = []
    for membership in elements:
        if str(membership.get("@type")) != "RequirementVerificationMembership":
            continue
        anchor_ids = reference_ids(membership.get("verifiedRequirement")) + (
            reference_ids(membership.get("memberElement"))
        )
        for anchor in anchor_ids:
            anchor_element = by_id.get(anchor)
            if anchor_element is None or str(anchor_element.get("@type")) != "RequirementUsage":
                continue
            anchors.append((anchor, anchor_element))
    if not anchors:
        raise RuntimeError(
            "no native RequirementVerificationMembership anchors a RequirementUsage "
            "with an API-resident verification case; native verification proof "
            "cannot be established"
        )

    # Identity grounding resolves only now that anchor candidates exist to
    # decide (c3/c5 fail-closed discipline). A missing validated kernel
    # binding raises IdentityNotFoundError; there is no name/type fallback.
    graph = build_relationship_graph(list(by_id.values()))
    resolver = traversal._lineage_resolver("Requirement", by_id, graph)
    bridge = _reference_subsetting_bridge(elements)

    for anchor, anchor_element in anchors:
        proof = _requirement_identity(
            anchor_element, resolver, bridge, by_id, traversal
        )
        if proof is None:
            continue
        subject_id, basis, provenance = proof
        subject = by_id[subject_id]
        # Case resolution stays delegated to the reviewed owner-chain
        # resolver, evaluated on the PROVEN subject.
        hops = (
            traversal.traverse("verifiedBy", anchor_element, elements)
            if subject_id == anchor
            else traversal.traverse("verifiedBy", subject, elements)
        )
        if not hops:
            continue
        case_id = element_id(hops[0].target)
        if case_id is None:
            continue
        return {
            "element_id": subject_id,
            "sysml_type": str(subject.get("@type")),
            "verification_case_id": case_id,
            "requirement_identity": {
                "basis": basis,
                "grounding_provenance": provenance,
                "requirement_lineage_root_id": resolver["root_id"],
                "rvm_anchor_id": anchor,
            },
        }
    raise RuntimeError(
        "no native RequirementVerificationMembership anchor resolves to a "
        "governed DE4SDV Requirement usage with an API-resident verification "
        "case through the reviewed verifiedBy resolver; native verification "
        "proof cannot be established"
    )


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
        "ontology": binding.ontology.to_dict(),
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
    proof_b_results: dict[str, dict[str, Any]] = {}
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            surface = validate_tool_surface(listed.tools)

            results["model_status"] = _structured(
                await session.call_tool("model_status", {}), "model_status"
            )
            # ---------------- Proof A: blocked EvidenceContract state -------
            # Root: the intended EvidenceContract-review requirement. Proof A
            # does NOT need to prove native verification on this requirement.
            results["resolve_element"] = _structured(
                await session.call_tool(
                    "resolve_element",
                    {"identifier": "reqCommandEmergencyBraking"},
                ),
                "resolve_element",
            )
            proof_a_root_id = results["resolve_element"]["element"]["element_id"]
            results["inspect_element"] = _structured(
                await session.call_tool(
                    "inspect_element", {"identifier": proof_a_root_id}
                ),
                "inspect_element",
            )
            proof_a_neighbors = _structured(
                await session.call_tool(
                    "semantic_neighbors", {"identifier": proof_a_root_id}
                ),
                "semantic_neighbors",
            )
            proof_a_coverage = _structured(
                await session.call_tool(
                    "verification_coverage",
                    {"requirement_identifier": proof_a_root_id},
                ),
                "verification_coverage",
            )
            results["semantic_neighbors"] = proof_a_neighbors
            results["verification_coverage"] = proof_a_coverage

            # ---------------- Proof B: independent native verification ------
            # Subject: selected from NATIVE API membership facts — a
            # RequirementUsage verified by a RequirementVerificationMembership
            # whose case element is API-resident. No name, package, or file
            # heuristic participates; the same selection runs in tests. The
            # subject may differ from the Proof-A root; impact, coverage, and
            # trace are all evaluated on THIS subject.
            contract = KernelContract.load(ontology_path)
            repository = SysMLRepository(ApiClient(api_url, timeout=600.0))
            elements = repository.list_elements(
                binding.sysml_project_id, binding.sysml_commit_id
            )
            traversal = SemanticTraversal(
                contract,
                kernel_bindings=KernelBindingIndex.from_binding(binding),
            )
            subject = _select_native_verification_subject(elements, traversal)
            subject_id = subject["element_id"]
            results["native_verification_subject"] = {
                "element_id": subject_id,
                "sysml_type": subject["sysml_type"],
                "verification_case_id": subject["verification_case_id"],
                "requirement_identity": subject["requirement_identity"],
                "selection": (
                    "RequirementVerificationMembership anchored on a "
                    "RequirementUsage; the anchored usage's governed DE4SDV "
                    "Requirement identity is machine-proven (direct "
                    "Requirement-lineage grounding or the reviewed "
                    "ReferenceSubsetting shadow bridge) and the verification "
                    "case resolves through the reviewed verifiedBy resolver"
                ),
            }
            proof_b_impact = _structured(
                await session.call_tool(
                    "impact", {"identifier": subject_id}
                ),
                "impact",
            )
            verification_case_ids = sorted(
                edge["target"]
                for edge in proof_b_impact["edges"]
                if edge["predicate"] == "verifiedBy"
            )
            if not verification_case_ids:
                raise RuntimeError(
                    "native verification subject produced no verifiedBy edge "
                    "through the impact surface"
                )
            proof_b_coverage = _structured(
                await session.call_tool(
                    "verification_coverage",
                    {"requirement_identifier": subject_id},
                ),
                "verification_coverage",
            )
            proof_b_trace = _structured(
                await session.call_tool(
                    "trace",
                    {
                        "source_identifier": subject_id,
                        "target_identifier": verification_case_ids[0],
                        "max_depth": 4,
                    },
                ),
                "trace",
            )
            # The seven-tool surface record keeps the Proof-A results; the
            # Proof-B results are validated explicitly as the second proof.
            results["impact"] = proof_b_impact
            results["trace"] = proof_b_trace
            proof_b_results = {
                "impact": proof_b_impact,
                "coverage": proof_b_coverage,
                "trace": proof_b_trace,
            }

    validate_semantic_results(
        results,
        expected_revision=expected_revision,
        proof_b_impact=proof_b_results["impact"],
        proof_b_coverage=proof_b_results["coverage"],
        proof_b_trace=proof_b_results["trace"],
        proof_b_subject=results.get("native_verification_subject"),
    )
    # Only the seven required proof tools count as exercised; the native
    # verification subject record is proof metadata, not a tool result.
    exercised_tools = {
        name: value for name, value in results.items() if name in REQUIRED_SEMANTIC_PROOF_TOOLS
    }
    return {
        "schema": "de4sdv-semantic-mcp-validation/v2",
        "read_only": True,
        "revision": expected_revision,
        "proof_a_blocked_evidence_contract": True,
        "proof_b_native_verification": True,
        "proof_a_root": proof_a_root_id,
        "proof_b_subject": results.get("native_verification_subject"),
        "native_verification_subject": results.get(
            "native_verification_subject"
        ),
        # Output clarity: ``tool_count`` keeps its backward-compatible meaning
        # (the exercised required proof tools). ``exposed_tool_count`` is the
        # declared surface, which may include additive strictly read-only
        # tools that this proof counts - and validates annotations for - but
        # does not call.
        "exposed_tool_count": surface["exposed_tool_count"],
        "exercised_tool_count": len(exercised_tools),
        "tool_count": len(exercised_tools),
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
                "exposed_tool_count": result["exposed_tool_count"],
                "exercised_tool_count": result["exercised_tool_count"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
