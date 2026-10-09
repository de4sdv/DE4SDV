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

Proof A - resolved EvidenceContract range (model authority, owner decision 5,
2026-10-07): the ``hasRelevantEvidenceContract`` discriminator is adopted
(range = the EvidenceContract type closure), so the Proof-A requirement must
expose at least one evidence-contract edge, the predicate must not be
reported as blocked, and verification coverage must carry the evidence
contracts; neighbors and coverage must stay subject-coherent. (The blocked
proof of the retired legacy/O3 authorities was removed in O4 Wave C2.)

Proof B - native verification still works: ``verifiedBy`` is an independently
reviewed native ``Requirement -> VerificationCase`` relation grounded in
``RequirementVerificationMembership``; its proof never depends on the
EvidenceContract route. The declared source domain is enforced by the
SEMANTIC RUNTIME itself (the ``verification-membership`` traversal strategy
grounds every queried source in the validated Requirement lineage; c5 R2
verifiedBy-domain closure), so this proof and ordinary semantic queries make
the same domain-valid claim. The subject is selected from native API
membership facts (never from names or layout) with its governed Requirement
identity proven through the runtime-owned identity rule (direct
Requirement-lineage grounding, or the reviewed ReferenceSubsetting shadow
bridge) and recorded for a defense-in-depth assertion. The proof exercises a
real verification case through the supported query surfaces with
``native-verification`` semantic strength and exact revision provenance. The
hasSubject / native-reference subject surface stays asserted on the PROOF-A
requirement: on the retained model no natively verified requirement usage
carries a member-product subject hop, while requirements without native
verification do (measured; see the c5 review Section 17.2), so demanding
that surface from the Proof-B subject would demand a fact the declared
semantics never placed there.

"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.sysml_api.repository import element_id, reference_ids

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

#: ``results`` entries that are proof METADATA rather than MCP tool results.
#: The revision gate in :func:`validate_semantic_results` binds tool OUTPUTS
#: to the expected revision; the Proof-B subject record documents the
#: selection and is not a tool output. Unknown keys are still refused.
NON_TOOL_RESULT_KEYS = frozenset({"native_verification_subject"})

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


def require_resolved_evidence_state(
    neighbors: dict[str, Any], coverage: dict[str, Any]
) -> None:
    """Proof A under ``model`` authority: the EvidenceContract range resolves.

    Owner decision 5 (2026-10-07) adopts the ``hasRelevantEvidenceContract``
    discriminator (range = the EvidenceContract type closure). Under the
    model-authority runtime the Proof-A requirement must therefore expose at
    least one evidence-contract edge, the predicate must no longer be
    reported as blocked, and coverage must carry the evidence contracts; the
    results must stay subject-coherent.
    """
    root_id = (neighbors.get("root") or {}).get("element_id")
    coverage_subject = (coverage.get("requirement") or {}).get("element_id")
    if not root_id or not coverage_subject:
        raise RuntimeError("Proof A results do not expose their requirement identities")
    if root_id != coverage_subject:
        raise RuntimeError(
            "Proof A is not subject-coherent: semantic_neighbors root "
            f"{root_id} != verification_coverage requirement {coverage_subject}"
        )
    edges = [
        edge
        for edge in neighbors.get("edges", [])
        if edge.get("predicate") == "hasRelevantEvidenceContract"
    ]
    if not edges:
        raise RuntimeError(
            "model authority: semantic_neighbors exposed no "
            "hasRelevantEvidenceContract edge for the Proof-A requirement"
        )
    for item in [*neighbors.get("unsupported_predicates", []),
                 *coverage.get("unsupported_predicates", [])]:
        if isinstance(item, dict) and item.get("predicate") == "hasRelevantEvidenceContract":
            raise RuntimeError(
                "model authority still reports hasRelevantEvidenceContract as "
                f"unsupported/blocked: {item}"
            )
    if not coverage.get("evidence_contracts"):
        raise RuntimeError(
            "model authority: verification_coverage carries no evidence_contracts "
            "for the Proof-A requirement"
        )


def require_proof_a(neighbors: dict[str, Any], coverage: dict[str, Any]) -> None:
    """Proof A under the model authority: the EvidenceContract range resolves."""
    require_resolved_evidence_state(neighbors, coverage)


def server_authority_arguments(
    *,
    authority: str | None,
    model_bundle_path: "str | Path | None" = None,
    model_bundle_id: str | None = None,
    allow_candidate_bundle: bool = False,
) -> list[str]:
    """The stdio server's authority flags (same selection as the in-process runtime)."""
    return [
        *(["--semantic-authority", str(authority)] if authority is not None else []),
        *(["--model-authority-bundle", str(model_bundle_path)]
          if model_bundle_path is not None else []),
        *(["--model-authority-bundle-id", model_bundle_id]
          if model_bundle_id is not None else []),
        *(["--allow-candidate-bundle"] if allow_candidate_bundle else []),
    ]


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
        if name in NON_TOOL_RESULT_KEYS:
            # Proof metadata, not a tool result: the revision gate binds tool
            # OUTPUTS to the expected revision; the subject record documents
            # the Proof-B selection (see _native_verification_subject_record).
            continue
        if name not in REQUIRED_SEMANTIC_PROOF_TOOLS:
            raise RuntimeError(
                f"unexpected MCP result key: {name!r}; only the seven proof "
                "tools and known proof metadata may appear in results"
            )
        if result.get("revision") != expected_revision:
            raise RuntimeError(
                f"{name} revision mismatch: {result.get('revision')} != {expected_revision}"
            )
    status = results["model_status"]
    if not status.get("current_baseline") or not status.get("read_only"):
        raise RuntimeError("model_status did not prove a read-only current baseline")
    # Proof A: the adopted discriminator resolves the EvidenceContract range.
    proof_a_neighbors = results["semantic_neighbors"]
    proof_a_coverage = results["verification_coverage"]
    require_proof_a(proof_a_neighbors, proof_a_coverage)
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


def _select_native_verification_subject(
    elements: list[dict[str, Any]], traversal: Any
) -> dict[str, Any]:
    """Select the Proof-B subject from native membership facts only.

    The subject must satisfy BOTH conditions (c5 R2 verifiedBy-domain
    closure):

    1. governed DE4SDV Requirement identity (the declared ``verifiedBy``
       source domain) — proven by the RUNTIME-owned identity rule
       (:meth:`SemanticTraversal.requirement_identity`): direct
       Requirement-lineage grounding of the anchored usage, or the reviewed
       ReferenceSubsetting shadow bridge followed by that grounding proof on
       the declared usage; and
    2. a native verification case resolvable through the reviewed owner-chain
       ``verifiedBy`` resolver itself (``traversal.traverse("verifiedBy", …)``
       on the PROVEN subject — the same domain-enforcing public traversal
       every ordinary semantic query uses).

    Fails closed on anything else: an ungrounded ``RequirementUsage`` (a bare
    API ``@type`` never establishes identity), a Need-role usage (sibling
    lineage), an acceptance-criterion-shaped usage outside the Requirement
    lineage, or a proven subject whose case does not resolve. No name,
    package, file, or source-text heuristic participates; anchor enumeration
    order is the export's deterministic order.

    Measured on the retained model (c5 R2 review): all 64 direct RVM anchors
    are serialized shadows; resolved through the reviewed shadow bridge, 30
    anchored usages ground explicitly in the Requirement lineage
    (acceptance-criterion-role usages) while 34 remain unresolved
    (evidence-contract-role usages whose definitions carry no lineage) and
    fail closed. The semantic runtime enforces the declared domain on the
    public predicate; this selector consumes the runtime-supported identity
    evidence for subject choice and records it for the defense-in-depth
    assertion — it never compensates for a broader public traversal.
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

    # Runtime-owned identity rule (one reviewed mechanism; the validator
    # does not define a stronger semantic rule than the semantic runtime).
    # The context is built only now that anchor candidates exist to decide
    # (c3/c5 fail-closed discipline): a missing validated kernel binding
    # raises IdentityNotFoundError; there is no name/type fallback.
    context = traversal.requirement_identity_context(elements)

    for anchor, anchor_element in anchors:
        identity = traversal.requirement_identity(
            anchor_element, elements, context=context
        )
        if identity is None:
            continue
        subject = by_id[identity["element_id"]]
        # Case resolution stays delegated to the reviewed owner-chain
        # resolver — evaluated on the PROVEN subject through the public
        # domain-enforcing traversal.
        hops = traversal.traverse("verifiedBy", subject, elements)
        if not hops:
            continue
        case_id = element_id(hops[0].target)
        if case_id is None:
            continue
        return {
            "element_id": identity["element_id"],
            "sysml_type": str(subject.get("@type")),
            "verification_case_id": case_id,
            "requirement_identity": {
                "basis": identity["basis"],
                "grounding_provenance": identity["grounding_provenance"],
                "requirement_lineage_root_id": identity[
                    "requirement_lineage_root_id"
                ],
                "rvm_anchor_id": anchor,
            },
        }
    raise RuntimeError(
        "no native RequirementVerificationMembership anchor resolves to a "
        "governed DE4SDV Requirement usage with an API-resident verification "
        "case through the reviewed verifiedBy resolver; native verification "
        "proof cannot be established"
    )


def _native_verification_subject_record(subject: dict[str, Any]) -> dict[str, Any]:
    """Proof-B subject record — proof METADATA, never a tool result.

    It documents the independent native-verification subject selection and
    deliberately carries NO ``revision`` field: the revision gate in
    :func:`validate_semantic_results` binds MCP tool OUTPUTS to the expected
    revision, and this record is not a tool output.
    """
    return {
        "element_id": subject["element_id"],
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


async def run_mcp_validation(
    *,
    api_url: str,
    binding_path: Path,
    expected_git_revision: str,
    authority: str | None = None,
    model_bundle_path: str | Path | None = None,
    model_bundle_id: str | None = None,
    allow_candidate_bundle: bool = False,
) -> dict[str, Any]:
    from de4sdv.semantic import entry_authority

    if model_bundle_id is not None and not entry_authority.is_model_bundle_id(model_bundle_id):
        raise ValueError(
            "model-authority bundle ID must be a literal mab-<32 or 64 lowercase hex> token"
        )
    # The stdio server changes cwd; both processes must read the caller's files.
    binding_path = binding_path.resolve()
    if model_bundle_path is not None:
        model_bundle_path = Path(model_bundle_path).resolve()
    model_request = entry_authority.resolve_model_request(
        authority=authority, bundle_path=model_bundle_path, bundle_id=model_bundle_id,
        environ={},
    )
    runtime, selection = entry_authority.build_model_runtime(
        model_request, api_url=api_url, binding_path=binding_path,
        expected_git_revision=expected_git_revision,
        **({"require_activation_eligible": False} if allow_candidate_bundle else {}),
    )
    binding = runtime.binding
    binding.require_current(expected_git_revision)
    binding.require_semantic_authority(runtime.contract.identity)
    if binding.scope != "full-model":
        raise RuntimeError(f"MCP proof requires full-model scope, got {binding.scope}")
    expected_revision = {
        "git_commit": binding.git_commit,
        "sysml_project_id": binding.sysml_project_id,
        "sysml_commit_id": binding.sysml_commit_id,
        "binding_status": "synchronized",
        "scope": "full-model",
        "semantic_authority": binding.semantic_authority.to_dict(),
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
            *server_authority_arguments(
                authority=authority or "model", model_bundle_path=model_bundle_path,
                model_bundle_id=model_bundle_id,
                allow_candidate_bundle=allow_candidate_bundle,
            ),
        ],
        cwd=ROOT,
        # The MCP client passes only a default environment; forward the corpus snapshot directory.
        env={**get_default_environment(),
             **{key: os.environ[key] for key in ("DE4SDV_SEMANTIC_SNAPSHOT_DIR",) if key in os.environ}},
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
            elements = runtime.repository.list_elements(
                binding.sysml_project_id, binding.sysml_commit_id
            )
            subject = _select_native_verification_subject(elements, runtime.traversal)
            subject_id = subject["element_id"]
            results["native_verification_subject"] = (
                _native_verification_subject_record(subject)
            )
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

    server_authority_id = (
        results["model_status"].get("semantic_authority") or {}
    ).get("id")
    if server_authority_id != runtime.semantic_authority_id:
        raise RuntimeError(
            "MCP server/Proof-B runtime authority mismatch: "
            f"{server_authority_id!r} != {runtime.semantic_authority_id!r}"
        )
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
        "semantic_authority": selection.provenance(),
        "proof_a_resolved_evidence_contract": True,
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
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--semantic-authority",
                        help="model (the only accepted value; default DE4SDV_SEMANTIC_AUTHORITY)")
    parser.add_argument("--model-authority-bundle")
    parser.add_argument("--model-authority-bundle-id")
    parser.add_argument("--allow-candidate-bundle", action="store_true",
                        help="serve an unclosed candidate bundle (privileged evidence steps only)")
    args = parser.parse_args()
    result = anyio.run(
        lambda: run_mcp_validation(
            api_url=args.api_url,
            binding_path=args.binding,
            expected_git_revision=args.expected_git_revision,
            authority=args.semantic_authority,
            model_bundle_path=args.model_authority_bundle,
            model_bundle_id=args.model_authority_bundle_id,
            allow_candidate_bundle=args.allow_candidate_bundle,
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
