"""O1 c5 — relevance and RFLP realization semantic review (PR #249).

Covers the c5 batch for exactly four identities:

- ``realizedBy`` — Outcome D: the executable AllocationUsage witness is a
  bounded cross-layer requirement-allocation trace (all ten real
  requirement-sourced allocations are Requirement -> Function; zero
  Logical/Physical/other), never a realization; the identity name overclaims
  and is recorded ``rename-required``; the real serialized shape returns zero
  hops through the configured source property.
- ``specifiesFunction`` — Outcome D: the modeled fact is a requirement-to-
  function relevance trace; a generic Dependency does not prove
  specification; ``rename-required`` recorded; relevance semantics retained.
- ``hasRelevantArchitecture`` — Outcome B: native Dependency witness plus
  load-bearing DE4SDV restrictions (Requirement domain, part/action
  constituent filter, MemberProduct-lineage exclusion); retained.
- ``hasRelevantEvidenceContract`` — c5 correction (independent review):
  Outcome B blocked/deferred. The declared ``Requirement -> EvidenceContract``
  range has NO machine-resolvable discriminator at the reviewed revision —
  native verification membership is supporting evidence only and also admits
  the acceptance-criterion role — so the range gate fails closed and emits
  nothing. Acceptance-criterion-role hops after correction must be 0; no
  returned target may exist without proven EvidenceContract identity.

The batch tests:

1.  exactly the four identities comprise c5; the global parity-reviewed set
    is c1(7) + c2(2) + c3(1) + c4(1) + c5(3) = 14 — the corrected
    EvidenceContract row is governed ``blocked``/``defer``, not parity;
2.  the reviewed rows: dispositions, targets, evidence state, forward-only
    required evidence, populated exact-fit decisions, non-empty unknowns for
    the blocked row;
3.  the ``rename-required`` schema extension is validated (distinct from
    defer/retired; vocabulary-locked);
4.  the hardened traversal laws: Requirement-domain enforcement,
    EvidenceContract fail-closed range gate (supporting evidence present,
    identity unprovable, nothing emitted), candidate-first quiet absence,
    missing-binding fail-closed, MemberProduct exclusion, disjointness, no
    name-based fallback;
5.  the retained-run replay numbers are locked (supporting evidence only;
    pre-c5 140, rejected c5-execution 34, corrected 0);
6.  ImpactService consumer behavior matches the reviewed semantics;
7.  c1-c4/K/PLE/c4 retirement unchanged; no .sysml, ontology YAML, or
    allocatedTo/deployedTo change by this batch;
8.  the generated inventory reproduces the reviewed decisions (red between
    Commit A and Commit B by design — the two-commit binding gate).

"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic import authority_inventory as ai
from de4sdv.semantic.kernel_contract import KernelContract

REPO_ROOT = Path(__file__).resolve().parents[1]

INVENTORY_PATH = (
    REPO_ROOT / "docs/method-conformance/o1/semantic-authority-inventory.json"
)
DECISIONS_PATH = (
    REPO_ROOT / "docs/method-conformance/o1/authority-review-decisions.yaml"
)
REVIEW_DOC = (
    REPO_ROOT / "docs/method-conformance/o1/c5-relevance-realization-review.md"
)
ONTOLOGY_PATH = REPO_ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
TRAVERSAL_SOURCE = REPO_ROOT / "de4sdv/semantic/traversal.py"

C5_IDENTITIES: tuple[str, ...] = (
    "realizedBy",
    "specifiesFunction",
    "hasRelevantArchitecture",
    "hasRelevantEvidenceContract",
)

C5_STAGE = "c5 (relevance and realization review batch)"
RENAME_DISPOSITION = "rename-required"

#: The seven c1 identities accepted as parity-reviewed (unchanged by c5).
C1_ACCEPTED: tuple[str, ...] = (
    "MethodPhase",
    "MethodContractObligation",
    "EvaluationSourceKind",
    "EvaluationScopeMembership",
    "TestedScopeDeclaration",
    "RetainedExecutionRecordReference",
    "AcceptanceAttestationReference",
)

C1_INCOMPLETE: tuple[str, ...] = ("MethodEvaluationScope",)
C2_IDENTITIES: tuple[str, ...] = ("VerificationCase", "verifiedBy")
C3_IDENTITIES: tuple[str, ...] = ("hasSubject",)
C4_IDENTITIES: tuple[str, ...] = ("derivesNeedFromConcern",)

PLE_GATED: tuple[str, ...] = (
    "FeatureConfiguration",
    "specifiesFeature",
    "specifiesCommonCapability",
    "appliesToMemberProduct",
    "selectsFeature",
    "includesCommonCapability",
    "variesAt",
    "selectsVariant",
)

K_TRIPLE: tuple[str, ...] = (
    "DerivesFromNeed",
    "derivesRequirementFromNeed",
    "derivedRequirementsOfNeed",
)

BLOCKED_ROWS_AFTER_C5: tuple[str, ...] = tuple(
    sorted(
        PLE_GATED
        + (
            "allocatedTo",
            "deployedTo",
            "instantiatesCanonicalArchitecture",
            "validatedBy",
            "validatesFitnessForUse",
            "hasRelevantEvidenceContract",
        )
    )
)

#: The c5 rows that remain on the global parity-reviewed set after the
#: correction; the EvidenceContract row is governed ``blocked``/``defer``.
C5_PARITY_ROWS: tuple[str, ...] = (
    "realizedBy",
    "specifiesFunction",
    "hasRelevantArchitecture",
)
C5_BLOCKED_ROWS: tuple[str, ...] = ("hasRelevantEvidenceContract",)

#: Retained-run replay literals (full-model candidate export at
#: 0a23902370de9fc74d6118afe480382e0b0d8aa0; read offline; supporting
#: evidence only, not current-head privileged closure).
REPLAY_REALIZEDBY_REAL_HOPS = 0
REPLAY_ALLOCATION_OBJECTS = 71
REPLAY_REQUIREMENT_SOURCED_ALLOCATIONS = 10
REPLAY_REALIZEDBY_FUNCTION_LAYER = 10
REPLAY_REALIZEDBY_LOGICAL_LAYER = 0
REPLAY_REALIZEDBY_PHYSICAL_LAYER = 0
REPLAY_REALIZEDBY_OTHER_LAYER = 0
REPLAY_REALIZEDBY_INVALID = 0
REPLAY_SPECIFIESFUNCTION_HOPS = 16
REPLAY_SPECIFIESFUNCTION_SOURCES = 15
REPLAY_HRA_PRE = 143
REPLAY_HRA_POST = 42
REPLAY_HRA_REJECTED = 101
#: hasRelevantEvidenceContract correction accounting. Pre-c5 140 hops were
#: the unhardened result; the executed c5 enforcement returned an over-broad
#: 34 hops over 29 distinct sources (not semantic parity — a measured
#: wrong/broader population, rejected by the independent review); the
#: corrected range gate emits nothing: 0 hops over 0 sources.
REPLAY_HEC_PRE = 140
REPLAY_HEC_PRE_SOURCES = 90
REPLAY_HEC_REJECTED_QUERY_DOMAIN = 89
REPLAY_HEC_REQUIREMENT_QUERIED = 51
REPLAY_HEC_REQUIREMENT_QUERIED_UNVERIFIED = 17
REPLAY_HEC_REJECTED_UNVERIFIED_SOURCES = 56
REPLAY_HEC_NEED_SOURCES = 4
REPLAY_HEC_NEED_HOPS = 7
REPLAY_HEC_ORDINARY_VERIFIED_HOPS = 0
#: Classification of the rejected over-broad c5-execution result (34 hops /
#: 29 distinct returned sources):
REPLAY_HEC_EXECUTED_C5 = 34
REPLAY_HEC_EXECUTED_C5_SOURCES = 29
REPLAY_HEC_ACCEPTANCE_CRITERION_HOPS = 16
REPLAY_HEC_ACCEPTANCE_CRITERION_SOURCES = 14
REPLAY_HEC_UNRESOLVED_AMBIGUOUS_HOPS = 18
REPLAY_HEC_UNRESOLVED_AMBIGUOUS_SOURCES = 15
#: The full pre-c5 population holds 16 ambiguous candidates: one of them
#: (evidenceContractSourceIdentity) appears only under a need-queried hop
#: that the Requirement-domain gate already rejects.
REPLAY_HEC_UNRESOLVED_CANDIDATE_SOURCES = 16
#: The corrected (post-correction) replay:
REPLAY_HEC_CORRECTED = 0
REPLAY_HEC_CORRECTED_SOURCES = 0


def _contract() -> KernelContract:
    return KernelContract.load(ONTOLOGY_PATH)


@pytest.fixture(scope="module")
def inventory() -> dict:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def decisions() -> dict:
    return yaml.safe_load(DECISIONS_PATH.read_text(encoding="utf-8"))


def _entries(inventory: dict, names=None) -> dict[str, dict]:
    by_identity = {entry["identity"]: entry for entry in inventory["entries"]}
    if names is None:
        return by_identity
    return {name: by_identity[name] for name in names}


def _decision_text(row: dict) -> str:
    parts = [str(row.get("note") or ""), str(row.get("exact_fit_decision") or "")]
    parts.extend(str(item) for item in row.get("required_evidence") or [])
    parts.extend(str(item) for item in row.get("unknowns") or [])
    return "\n".join(parts)


def _review_text() -> str:
    """Whitespace-normalized review-doc text (markdown wraps lines)."""
    return " ".join(REVIEW_DOC.read_text(encoding="utf-8").split())


# ---------------------------------------------------------------------------
# Scope, decisions, and inventory state
# ---------------------------------------------------------------------------


class TestC5ScopeAndCounts:
    def test_c5_is_exactly_four_identities(self):
        assert C5_IDENTITIES == (
            "realizedBy",
            "specifiesFunction",
            "hasRelevantArchitecture",
            "hasRelevantEvidenceContract",
        )

    def test_only_c5_identities_carry_the_c5_stage(self, inventory):
        staged = [
            entry["identity"]
            for entry in inventory["entries"]
            if str(entry["reviewed"]["stage"]).startswith("c5")
        ]
        assert sorted(staged) == sorted(C5_IDENTITIES)

    def test_global_parity_set_advances_by_exactly_the_c5_rows(self, inventory):
        """This file owns the global parity-reviewed set from c5 onward.
        c1(7) + c2(2) + c3(1) + c4(1) + c5(3) = 14: the corrected
        EvidenceContract row is governed ``blocked``, not parity."""
        parity = {
            entry["identity"]
            for entry in inventory["entries"]
            if entry["reviewed"]["evidence_state"] == "parity-reviewed"
        }
        assert parity == (
            set(C1_ACCEPTED)
            | set(C2_IDENTITIES)
            | set(C3_IDENTITIES)
            | set(C4_IDENTITIES)
            | set(C5_PARITY_ROWS)
        )
        assert len(parity) == 14
        assert not (set(C5_BLOCKED_ROWS) & parity)

    def test_authority_current_remains_legacy_yaml(self, inventory):
        for identity in C5_IDENTITIES:
            entry = _entries(inventory, (identity,))[identity]
            assert entry["reviewed"]["authority_current"] == "legacy-yaml", identity

    def test_expected_evidence_state_counts(self, inventory):
        """c5 advanced evidence maturity for its rows (repository-evidenced
        65 -> 61, parity 11 -> 15); the correction moves the EvidenceContract
        row back out of parity into the governed blocked state: parity 14 /
        blocked 14 / repository-evidenced 61."""
        assert inventory["evidence_state_counts"] == {
            "blocked": 14,
            "parity-reviewed": 14,
            "privileged-closure-proven": 3,
            "repository-evidenced": 61,
            "unknown": 1,
        }

    def test_authority_target_counts_unchanged(self, inventory):
        """Both rename rows keep their location targets; no target counts move."""
        assert inventory["authority_target_counts"] == {
            "accepted-library-grounded": 12,
            "de4sdv-application-semantic": 4,
            "external-reference": 2,
            "model-authoritative": 61,
            "native-sysml": 7,
            "retired": 1,
            "unknown": 6,
        }

    def test_authority_current_counts_unchanged(self, inventory):
        assert inventory["authority_current_counts"] == {
            "accepted-library-grounded": 2,
            "external-reference": 3,
            "legacy-yaml": 78,
            "model-authoritative": 3,
            "native-sysml": 6,
            "unknown": 1,
        }

    def test_conditional_counts_unchanged(self, inventory):
        assert inventory["authority_target_conditional_counts"] == {
            "accepted-library-grounded": 8,
        }

    def test_blocked_rows_after_c5_are_exactly_expected(self, inventory):
        blocked = sorted(
            entry["identity"]
            for entry in inventory["entries"]
            if entry["reviewed"]["evidence_state"] == "blocked"
        )
        assert blocked == sorted(BLOCKED_ROWS_AFTER_C5)

    def test_c1_rows_unchanged(self, inventory):
        entries = _entries(inventory)
        for name in C1_ACCEPTED:
            row = entries[name]["reviewed"]
            assert row["authority_current"] == "legacy-yaml", name
            assert row["authority_target"] == "model-authoritative", name
            assert row["evidence_state"] == "parity-reviewed", name
        for name in C1_INCOMPLETE:
            row = entries[name]["reviewed"]
            assert row["evidence_state"] == "repository-evidenced", name

    def test_c2_rows_unchanged(self, inventory):
        entries = _entries(inventory)
        verification = entries["VerificationCase"]["reviewed"]
        assert verification["authority_current"] == "native-sysml"
        assert verification["evidence_state"] == "parity-reviewed"
        verified_by = entries["verifiedBy"]["reviewed"]
        assert verified_by["authority_target"] == "native-sysml"
        assert verified_by["evidence_state"] == "parity-reviewed"

    def test_c3_row_unchanged(self, inventory):
        row = _entries(inventory)["hasSubject"]["reviewed"]
        assert row["stage"] == "c3 (hasSubject review batch)"
        assert row["authority_target"] == "de4sdv-application-semantic"
        assert row["evidence_state"] == "parity-reviewed"

    def test_c4_retirement_unchanged(self, inventory):
        row = _entries(inventory)["derivesNeedFromConcern"]["reviewed"]
        assert row["authority_target"] == "retired"
        assert row["disposition"] == "retire-without-replacement"
        assert row["evidence_state"] == "parity-reviewed"

    def test_k_rows_unchanged(self, inventory):
        entries = _entries(inventory)
        for identity in K_TRIPLE:
            row = entries[identity]["reviewed"]
            assert row["authority_current"] == "model-authoritative", identity
            assert row["evidence_state"] == "privileged-closure-proven", identity
            assert row["closure_evidence_ref"] == "r6-3", identity

    def test_ple_rows_unchanged(self, inventory):
        entries = _entries(inventory)
        for identity in PLE_GATED:
            row = entries[identity]["reviewed"]
            assert row["evidence_state"] == "blocked", identity
            assert row["adoption_status"] == "pinned-not-adopted", identity
            assert row["conditional_target"] is True, identity


# ---------------------------------------------------------------------------
# Reviewed decisions (the source rows)
# ---------------------------------------------------------------------------


class TestReviewedDecisions:
    def _row(self, decisions, identity) -> dict:
        return decisions["entries"][identity]

    def test_stage_and_common_fields(self, decisions):
        for identity in C5_PARITY_ROWS:
            row = self._row(decisions, identity)
            assert row["stage"] == C5_STAGE, identity
            assert row["authority_current"] == "legacy-yaml", identity
            assert row["evidence_state"] == "parity-reviewed", identity
            assert row["adoption_status"] == "not-applicable", identity
            assert row["conditional_target"] is False, identity
            assert row["transition_gate"] is None, identity
            assert row["unknowns"] == [], identity
            assert row["closure_evidence_ref"] is None, identity
            assert row["semantic_text_equivalence"] is None, identity

    def test_evidencecontract_row_is_blocked_deferred(self, decisions):
        """c5 correction: the declared range is not machine-resolvable at the
        reviewed revision, so the row is governed blocked/defer — never
        parity-reviewed on a measured wrong/broader population."""
        row = self._row(decisions, "hasRelevantEvidenceContract")
        assert row["stage"] == C5_STAGE
        assert row["authority_current"] == "legacy-yaml"
        assert row["authority_target"] == "de4sdv-application-semantic"
        assert row["evidence_state"] == "blocked"
        assert row["disposition"] == "defer"
        assert row["adoption_status"] == "not-applicable"
        assert row["conditional_target"] is False
        assert isinstance(row["transition_gate"], str) and row["transition_gate"]
        assert row["unknowns"], "the unresolved discriminator must be recorded"
        assert row["closure_evidence_ref"] is None
        assert row["semantic_text_equivalence"] is None
        assert row["confidence"] in ("high", "medium", "low")
        text = _decision_text(row)
        # The exact blocker statement required by the independent review.
        assert (
            "EvidenceContract-specific identity is not machine-resolvable at "
            "the reviewed revision" in text
        )
        assert (
            "native verification membership also admits AcceptanceCriterion "
            "and therefore cannot establish the declared EvidenceContract "
            "range" in text
        )
        assert "34 hops over 29 distinct sources" in text
        assert "0 hops over 0 sources" in text
        assert "acceptance-criterion-role hops after correction: 0" in text
        unknowns = " ".join(str(item) for item in row["unknowns"])
        assert "identity discriminator" in unknowns
        assert "no shared specialization lineage" in unknowns

    def test_realizedby_is_rename_required(self, decisions):
        row = self._row(decisions, "realizedBy")
        assert row["disposition"] == RENAME_DISPOSITION
        assert row["authority_target"] == "model-authoritative"
        text = _decision_text(row)
        assert "Outcome D" in text
        assert "rename/replacement required" in text
        assert "allocation is not realization" in text
        assert "10 Function / 0 LogicalElement / 0 PhysicalElement / 0 other" in text
        assert "zero hops against the real serialized model" in text
        assert "not the canonical RFLP realization chain" in _review_text()

    def test_specifiesfunction_is_rename_required(self, decisions):
        row = self._row(decisions, "specifiesFunction")
        assert row["disposition"] == RENAME_DISPOSITION
        assert row["authority_target"] == "de4sdv-application-semantic"
        text = _decision_text(row)
        assert "Outcome D" in text
        assert "relevance" in text
        assert "does not prove specification" in text
        assert "no strengthening" in text

    def test_hasrelevantarchitecture_is_retained(self, decisions):
        row = self._row(decisions, "hasRelevantArchitecture")
        assert row["disposition"] == "prove-existing-model-authority"
        assert row["authority_target"] == "de4sdv-application-semantic"
        text = _decision_text(row)
        assert "Outcome B" in text
        assert "MemberProduct" in text
        assert "143" in text and "42" in text and "101" in text

    def test_hasrelevantevidencecontract_is_blocked_with_the_exact_blocker(
        self, decisions
    ):
        row = self._row(decisions, "hasRelevantEvidenceContract")
        assert row["disposition"] == "defer"
        assert row["evidence_state"] == "blocked"
        assert row["authority_target"] == "de4sdv-application-semantic"
        text = _decision_text(row)
        assert "Outcome B" in text
        assert "no machine-resolvable" in text
        assert "RequirementVerificationMembership != EvidenceContract automatically" in text
        assert "verified AcceptanceCriterion != EvidenceContract" in text
        assert "140" in text and "34" in text
        assert "acceptance-criterion-role" in text
        assert "wrong/broader population" in text

    def test_exact_fit_decisions_populated_and_not_native(self, decisions):
        for identity in C5_IDENTITIES:
            decision = self._row(decisions, identity)["exact_fit_decision"]
            assert isinstance(decision, str) and decision.strip(), identity
            assert decision.startswith("not exact"), identity

    def test_required_evidence_is_forward_only(self, decisions):
        """Completed c5 work must not remain under required_evidence; every
        item lists a forward migration stage (rename obligation, O2, O3)."""
        for identity in C5_IDENTITIES:
            items = self._row(decisions, identity)["required_evidence"]
            assert items, identity
            joined = " ".join(items)
            assert "O2 " in joined, identity
            assert "O3 " in joined, identity
            for banned in ("replay", "review completed", "c5 review", "test"):
                assert banned not in joined.lower(), (identity, banned)
        for identity in ("realizedBy", "specifiesFunction"):
            joined = " ".join(self._row(decisions, identity)["required_evidence"])
            assert "rename" in joined.lower(), identity
        joined = " ".join(
            self._row(decisions, "hasRelevantEvidenceContract")["required_evidence"]
        )
        assert "identity/lineage contract" in joined


# ---------------------------------------------------------------------------
# `rename-required` schema laws
# ---------------------------------------------------------------------------


class TestRenameRequiredSchema:
    def _observed(self) -> dict:
        return {
            "yaml_path": "relationships:probe",
            "domain": "Requirement",
            "range": "ArchitectureElement",
            "grounding_kind": "sysml_mapping",
            "strategy": "allocation",
            "semantic_strength": "allocation",
            "query_direction": None,
            "runtime_support": "implemented (allocation)",
        }

    def _row(self, **overrides) -> dict:
        row = {
            "authority_current": "legacy-yaml",
            "authority_target": "model-authoritative",
            "evidence_state": "parity-reviewed",
            "adoption_status": "not-applicable",
            "transition_gate": None,
            "conditional_target": False,
            "disposition": RENAME_DISPOSITION,
            "confidence": "high",
            "stage": "c5 (probe)",
            "note": "probe",
            "unknowns": [],
            "required_evidence": ["O2 probe", "O3 probe"],
            "exact_fit_decision": "not exact native fit",
            "closure_evidence_ref": None,
            "semantic_text_equivalence": None,
            "runtime_consumption": None,
        }
        row.update(overrides)
        return row

    def _problems(self, **overrides) -> list[str]:
        return ai._entry_problems(
            "probe", "relationship", self._observed(), self._row(**overrides), {}
        )

    def test_disposition_vocabulary_contains_rename_required(self):
        assert RENAME_DISPOSITION in ai.DISPOSITIONS

    def test_rename_required_is_not_a_target_or_current_location(self):
        assert RENAME_DISPOSITION not in ai.AUTHORITY_SOURCES
        assert RENAME_DISPOSITION not in ai.AUTHORITY_TARGETS

    def test_valid_rename_required_row_passes_validation(self):
        assert self._problems() == []

    def test_rename_required_keeps_a_location_target(self):
        """A rename-required entry keeps its location target (distinct from
        retired/unknown): the fact is retained, only the identity migrates."""
        for target in ("model-authoritative", "de4sdv-application-semantic"):
            assert self._problems(authority_target=target) == []

    def test_unknown_disposition_still_fails_closed(self):
        problems = self._problems(disposition="rename-or-something")
        assert any("outside the accepted" in problem for problem in problems)

    def test_rename_required_row_requires_forward_evidence(self):
        problems = self._problems(required_evidence=[])
        assert any("required_evidence" in problem for problem in problems)


# ---------------------------------------------------------------------------
# Hardened traversal laws (the c5 runtime contract)
# ---------------------------------------------------------------------------


def _binding_dict(kernel_bindings: list[dict[str, str]]) -> dict:
    return {
        "git_repository": "de4sdv/DE4SDV",
        "git_commit": "a" * 40,
        "sysml_project_id": "project-1",
        "sysml_commit_id": "commit-1",
        "import_timestamp": "2026-09-13T00:00:00Z",
        "import_tool_version": "test",
        "semantic_validation": "passed",
        "scope": "fixture",
        "ontology": _contract().identity.to_dict(),
        "kernel_bindings": kernel_bindings,
    }


def _kernel_bindings() -> list[dict[str, str]]:
    return [
        {
            "ontology_class": "Requirement",
            "element_id": "kernel-requirement",
            "source_file": "de4sdv_method_context.sysml",
            "declaration": "requirement def RequirementCandidate",
        },
        {
            "ontology_class": "Need",
            "element_id": "kernel-need",
            "source_file": "de4sdv_method_context.sysml",
            "declaration": "requirement def StakeholderNeedCandidate",
        },
        {
            "ontology_class": "MemberProduct",
            "element_id": "kernel-member-product",
            "source_file": "de4sdv_product_line.sysml",
            "declaration": "part def ProductLineMemberProduct",
        },
    ]


def _traversal(kernel_bindings: list[dict[str, str]] | None = None):
    from de4sdv.semantic.kernel_binding_index import KernelBindingIndex
    from de4sdv.semantic.traversal import SemanticTraversal
    from de4sdv.sysml_api.revisions import RevisionBinding

    if kernel_bindings is None:
        index = None
    else:
        index = KernelBindingIndex.from_binding(
            RevisionBinding.from_dict(_binding_dict(kernel_bindings))
        )
    return SemanticTraversal(_contract(), kernel_bindings=index)


def _elements() -> list[dict]:
    """Shared c5 fixture: typed requirement, typed need, part, verified and
    unverified requirement-like sources, action target, and the four
    relationship families."""
    ref = lambda value: {"@id": value}
    return [
        {"@id": "kernel-requirement", "@type": "RequirementDefinition",
         "declaredName": "RequirementCandidate"},
        {"@id": "kernel-need", "@type": "RequirementDefinition",
         "declaredName": "StakeholderNeedCandidate"},
        {"@id": "kernel-member-product", "@type": "PartDefinition",
         "declaredName": "ProductLineMemberProduct"},
        {"@id": "req-1", "@type": "RequirementUsage", "declaredName": "reqExample",
         "ownedRelationship": [ref("ft-req-1")]},
        {"@id": "ft-req-1", "@type": "FeatureTyping",
         "owningRelatedElement": ref("req-1"), "type": ref("kernel-requirement")},
        {"@id": "need-1", "@type": "RequirementUsage", "declaredName": "needExample",
         "ownedRelationship": [ref("ft-need-1")]},
        {"@id": "ft-need-1", "@type": "FeatureTyping",
         "owningRelatedElement": ref("need-1"), "type": ref("kernel-need")},
        {"@id": "action-1", "@type": "ActionUsage", "declaredName": "doIt"},
        {"@id": "part-plain", "@type": "PartUsage", "declaredName": "plainPart"},
        # specifiesFunction: outgoing requirement -> action.
        {"@id": "dep-sf", "@type": "Dependency",
         "source": [ref("req-1")], "target": [ref("action-1")]},
        # need -> action dependency: domain violation for specifiesFunction.
        {"@id": "dep-need-action", "@type": "Dependency",
         "source": [ref("need-1")], "target": [ref("action-1")]},
        # realizedBy fixture shape (source/target properties).
        {"@id": "alloc-1", "@type": "AllocationUsage",
         "source": [ref("req-1")], "target": [ref("action-1")]},
        # need-sourced allocation: domain violation for realizedBy.
        {"@id": "alloc-need-2", "@type": "AllocationUsage",
         "source": [ref("need-1")], "target": [ref("action-1")]},
        # hasRelevantArchitecture: incoming part -> requirement.
        {"@id": "dep-hra", "@type": "Dependency",
         "source": [ref("part-plain")], "target": [ref("req-1")]},
        # hEC: unverified requirement-usage source -> requirement.
        {"@id": "req-unverified", "@type": "RequirementUsage",
         "declaredName": "reqUnverified"},
        {"@id": "dep-ec-unverified", "@type": "Dependency",
         "source": [ref("req-unverified")], "target": [ref("req-1")]},
        # hEC: natively verified source, direct anchor.
        {"@id": "ec-1", "@type": "RequirementUsage",
         "declaredName": "evidenceContractX"},
        {"@id": "rvm-1", "@type": "RequirementVerificationMembership",
         "memberElement": ref("ec-1")},
        {"@id": "dep-ec-verified", "@type": "Dependency",
         "source": [ref("ec-1")], "target": [ref("req-1")]},
        # hEC: verified through the serialized shadow bridge.
        {"@id": "ec-2", "@type": "RequirementUsage",
         "declaredName": "evidenceContractY"},
        {"@id": "shadow-2", "@type": "ReferenceUsage", "declaredName": "shadow"},
        {"@id": "rs-2", "@type": "ReferenceSubsetting",
         "referencedFeature": ref("ec-2"), "owningRelatedElement": ref("shadow-2")},
        {"@id": "rvm-2", "@type": "RequirementVerificationMembership",
         "memberElement": ref("shadow-2")},
        {"@id": "dep-ec-shadow", "@type": "Dependency",
         "source": [ref("ec-2")], "target": [ref("req-1")]},
    ]


def _by_id(elements: list[dict]) -> dict[str, dict]:
    return {element["@id"]: element for element in elements}


def _targets(traversal, predicate: str, source_id: str, elements) -> list[str]:
    hops = traversal.traverse(predicate, _by_id(elements)[source_id], elements)
    return sorted(hop.target["@id"] for hop in hops)


class TestRequirementDomainEnforcement:
    """The declared Requirement domain is enforced on the queried source for
    all four predicates: API RequirementUsage is not DE4SDV Requirement."""

    def test_need_source_is_quiet_absence_for_specifies_function(self):
        traversal = _traversal(_kernel_bindings())
        assert _targets(traversal, "specifiesFunction", "req-1", _elements()) == [
            "action-1"
        ]
        assert _targets(traversal, "specifiesFunction", "need-1", _elements()) == []

    def test_need_source_is_quiet_absence_for_realized_by(self):
        traversal = _traversal(_kernel_bindings())
        assert _targets(traversal, "realizedBy", "req-1", _elements()) == ["action-1"]
        assert _targets(traversal, "realizedBy", "need-1", _elements()) == []

    def test_non_requirement_queries_are_quiet_absence(self):
        traversal = _traversal(_kernel_bindings())
        elements = _elements()
        assert _targets(traversal, "hasRelevantArchitecture", "part-plain", elements) == []
        assert _targets(traversal, "hasRelevantEvidenceContract", "action-1", elements) == []
        assert _targets(traversal, "hasRelevantEvidenceContract", "need-1", elements) == []

    def test_untagged_requirement_usage_is_not_grounded(self):
        """A RequirementUsage without a validated lineage grounding (for
        example a same-named element with no typing) is quiet absence — the
        API metaclass alone never proves DE4SDV Requirement."""
        traversal = _traversal(_kernel_bindings())
        elements = _elements() + [
            {"@id": "req-homonym", "@type": "RequirementUsage",
             "declaredName": "reqExample"},
            {"@id": "dep-homonym", "@type": "Dependency",
             "source": [{"@id": "req-homonym"}], "target": [{"@id": "action-1"}]},
        ]
        assert _targets(traversal, "specifiesFunction", "req-homonym", elements) == []

    def test_missing_binding_index_fails_closed_with_candidates(self):
        traversal = _traversal(None)
        with pytest.raises(Exception, match="no validated kernel binding index"):
            traversal.traverse("specifiesFunction", _by_id(_elements())["req-1"], _elements())

    def test_missing_binding_index_is_quiet_without_candidates(self):
        """Candidate-first: a queried source touching no configured
        relationship performs no lineage resolution (no binding required)."""
        traversal = _traversal(None)
        assert traversal.traverse(
            "specifiesFunction", _by_id(_elements())["action-1"], _elements()
        ) == []

    def test_missing_requirement_root_fails_closed(self):
        traversal = _traversal(_kernel_bindings())
        elements = [
            element for element in _elements() if element["@id"] != "kernel-requirement"
        ]
        with pytest.raises(Exception, match="does not exist in the bound revision"):
            traversal.traverse("specifiesFunction", _by_id(elements)["req-1"], elements)


class TestRealizedByLaws:
    def test_allocation_is_not_realization(self):
        """The hop keeps allocation strength and the row records the rename;
        nothing in the batch presents the witness as realization."""
        row = yaml.safe_load(DECISIONS_PATH.read_text(encoding="utf-8"))["entries"][
            "realizedBy"
        ]
        assert row["disposition"] == RENAME_DISPOSITION
        text = _decision_text(row)
        assert "AllocationUsage != realization automatically" in text
        assert "!= physical realization automatically" in text

    def test_requirement_sourced_allocation_is_bounded_allocation_trace(self):
        traversal = _traversal(_kernel_bindings())
        hops = traversal.traverse(
            "realizedBy", _by_id(_elements())["req-1"], _elements()
        )
        assert [hop.target["@id"] for hop in hops] == ["action-1"]
        assert hops[0].semantic_strength == "allocation"

    def test_generic_dependency_is_not_an_allocation(self):
        """A dependency with allocation-like endpoints is never a realizedBy
        witness (different relationship objects)."""
        traversal = _traversal(_kernel_bindings())
        elements = _elements()
        assert _targets(traversal, "realizedBy", "req-1", elements) == ["action-1"]
        dep_hops = [
            hop for hop in traversal.traverse(
                "realizedBy", _by_id(elements)["req-1"], elements
            )
            if hop.api_object["@id"] == "dep-sf"
        ]
        assert dep_hops == []


class TestSpecifiesFunctionLaws:
    def test_generic_dependency_is_not_specification(self):
        """The hop is relevance strength; the row records Outcome D for the
        overclaiming name and no specification semantics are claimed."""
        row = yaml.safe_load(DECISIONS_PATH.read_text(encoding="utf-8"))["entries"][
            "specifiesFunction"
        ]
        assert row["disposition"] == RENAME_DISPOSITION
        assert "does not prove specification" in _decision_text(row)
        traversal = _traversal(_kernel_bindings())
        hops = traversal.traverse(
            "specifiesFunction", _by_id(_elements())["req-1"], _elements()
        )
        assert [hop.target["@id"] for hop in hops] == ["action-1"]
        assert hops[0].semantic_strength == "relevance"

    def test_generic_dependency_is_not_verification_or_satisfaction(self):
        """Only the configured Dependency objects carry the predicate; no
        verification membership or subject semantics leak into it."""
        traversal = _traversal(_kernel_bindings())
        hops = traversal.traverse(
            "specifiesFunction", _by_id(_elements())["req-1"], _elements()
        )
        assert {hop.api_object["@type"] for hop in hops} == {"Dependency"}


def _acceptance_criterion_kernel_bindings() -> list[dict[str, str]]:
    return _kernel_bindings() + [
        {
            "ontology_class": "AcceptanceCriterion",
            "element_id": "ac-def",
            "source_file": "middleware_verification_evidence.sysml",
            "declaration": "requirement def MiddlewareAcceptanceCriterion",
        },
    ]


def _acceptance_criterion_elements() -> list[dict]:
    """A verified acceptance-criterion usage with the same verification and
    dependency structure as the evidence-contract candidates. It must never
    be emitted through the blocked EvidenceContract range."""
    ref = lambda value: {"@id": value}
    return [
        {"@id": "ac-def", "@type": "RequirementDefinition",
         "declaredName": "MiddlewareAcceptanceCriterion"},
        {"@id": "ac-1", "@type": "RequirementUsage",
         "declaredName": "acceptanceCriterionProbe"},
        {"@id": "ft-ac-1", "@type": "FeatureTyping",
         "owningRelatedElement": ref("ac-1"), "type": ref("ac-def")},
        {"@id": "rvm-ac", "@type": "RequirementVerificationMembership",
         "memberElement": ref("ac-1")},
        {"@id": "dep-ac", "@type": "Dependency",
         "source": [ref("ac-1")], "target": [ref("req-1")]},
    ]


def _ordinary_verified_requirement_elements() -> list[dict]:
    """A natively verified ordinary requirement (Requirement lineage) with
    the same dependency structure: verification membership never upgrades an
    ordinary requirement into an evidence contract."""
    ref = lambda value: {"@id": value}
    return [
        {"@id": "req-ord-1", "@type": "RequirementUsage",
         "declaredName": "reqOrdinaryVerified"},
        {"@id": "ft-req-ord", "@type": "FeatureTyping",
         "owningRelatedElement": ref("req-ord-1"),
         "type": ref("kernel-requirement")},
        {"@id": "rvm-ord", "@type": "RequirementVerificationMembership",
         "memberElement": ref("req-ord-1")},
        {"@id": "dep-ord", "@type": "Dependency",
         "source": [ref("req-ord-1")], "target": [ref("req-1")]},
    ]


class TestEvidenceContractBlockedRange:
    """The corrected range gate (c5 correction): native verification
    membership is supporting evidence only; no governed discriminator
    establishes EvidenceContract identity at the reviewed revision; nothing
    is emitted and every ambiguous verified usage fails closed.

    Laws locked here:

    - ``RequirementUsage != EvidenceContract automatically``;
    - ``RequirementVerificationMembership != EvidenceContract automatically``;
    - verified ``AcceptanceCriterion != EvidenceContract``;
    - ordinary verified ``Requirement != EvidenceContract``;
    - unverified ``Requirement != EvidenceContract``;
    - ``Need != Requirement`` (as queried source and as returned source);
    - generic ``Dependency != EvidenceContract identity``;
    - missing identity discriminator fails closed (non-vacuously: candidates
      and their supporting evidence are present).
    """

    def test_verified_requirement_usage_is_supporting_evidence_not_a_hop(self):
        """The fixture carries FULL verification support (direct anchor and
        shadow bridge) and the supporting relation resolves — yet nothing is
        emitted: the range identity cannot be established."""
        traversal = _traversal(_kernel_bindings())
        elements = _elements()
        supporting = traversal._natively_verified_ids(elements)
        assert {"ec-1", "ec-2"} <= supporting, "the fixture must be non-vacuous"
        assert _targets(
            traversal, "hasRelevantEvidenceContract", "req-1", elements
        ) == []

    def test_membership_presence_never_changes_the_outcome(self):
        """With the memberships removed and with them present, the outcome is
        identical (nothing emitted): the membership is supporting evidence,
        never sufficient, and never load-bearing for emission."""
        traversal = _traversal(_kernel_bindings())
        with_membership = _elements()
        without_membership = [
            element
            for element in with_membership
            if element["@type"] != "RequirementVerificationMembership"
        ]
        assert _targets(
            traversal, "hasRelevantEvidenceContract", "req-1", without_membership
        ) == []
        assert traversal._natively_verified_ids(with_membership), (
            "the verification support must be present in the with-membership fixture"
        )
        assert _targets(
            traversal, "hasRelevantEvidenceContract", "req-1", with_membership
        ) == []

    def test_missing_identity_discriminator_fails_closed(self):
        """The gate is exercised directly: every supporting signal present,
        no candidate proven — the fail-closed outcome is attributable to the
        missing exact discriminator, not to missing verification."""
        traversal = _traversal(_kernel_bindings())
        elements = _elements()
        assert traversal._natively_verified_ids(elements)
        assert traversal._evidence_contract_identity_ids(elements) == set()

    def test_unverified_shadow_only_does_not_qualify(self):
        """A ReferenceSubsetting whose declared feature is not anchored by a
        membership proves nothing."""
        traversal = _traversal(_kernel_bindings())
        elements = _elements() + [
            {"@id": "ec-3", "@type": "RequirementUsage",
             "declaredName": "evidenceContractZ"},
            {"@id": "shadow-3", "@type": "ReferenceUsage"},
            {"@id": "rs-3", "@type": "ReferenceSubsetting",
             "referencedFeature": {"@id": "ec-3"},
             "owningRelatedElement": {"@id": "shadow-3"}},
            {"@id": "dep-ec-shadow-only", "@type": "Dependency",
             "source": [{"@id": "ec-3"}], "target": [{"@id": "req-1"}]},
        ]
        assert _targets(
            traversal, "hasRelevantEvidenceContract", "req-1", elements
        ) == []

    def test_no_verification_memberships_means_no_evidence_contract_hops(self):
        traversal = _traversal(_kernel_bindings())
        elements = [
            element
            for element in _elements()
            if element["@type"] != "RequirementVerificationMembership"
        ]
        assert _targets(
            traversal, "hasRelevantEvidenceContract", "req-1", elements
        ) == []

    def test_unverified_source_is_quiet_absence(self):
        traversal = _traversal(_kernel_bindings())
        assert _targets(
            traversal, "hasRelevantEvidenceContract", "req-1", _elements()
        ) == []

    def test_verified_acceptance_criterion_is_not_an_evidence_contract(self):
        """A nested verified acceptance-criterion usage — grounded through
        the kernel-bound acceptance-criterion declaration, otherwise
        verification- and dependency-identical to the evidence-contract
        candidates — never becomes an evidence-contract hop. Under the
        rejected enforcement this shape WOULD have been emitted (the
        supporting relation resolves)."""
        traversal = _traversal(_acceptance_criterion_kernel_bindings())
        elements = _elements() + _acceptance_criterion_elements()
        by_id = _by_id(elements)
        assert traversal.kernel_bindings is not None
        assert (
            traversal.kernel_bindings.element_id_for("AcceptanceCriterion", by_id)
            == "ac-def"
        )
        assert "ac-1" in traversal._natively_verified_ids(elements)
        assert _targets(
            traversal, "hasRelevantEvidenceContract", "req-1", elements
        ) == []

    def test_ordinary_verified_requirement_is_not_an_evidence_contract(self):
        """A natively verified requirement usage inside the Requirement
        lineage is an ordinary verified requirement — verification alone
        never establishes the EvidenceContract range."""
        traversal = _traversal(_kernel_bindings())
        elements = _elements() + _ordinary_verified_requirement_elements()
        assert "req-ord-1" in traversal._natively_verified_ids(elements)
        assert _targets(
            traversal, "hasRelevantEvidenceContract", "req-1", elements
        ) == []

    def test_need_is_not_a_requirement_and_never_a_hop(self):
        """Need != Requirement: a need-typed returned source and a
        need-queried source both fail closed."""
        traversal = _traversal(_kernel_bindings())
        elements = _elements() + [
            {"@id": "dep-need-to-req", "@type": "Dependency",
             "source": [{"@id": "need-1"}], "target": [{"@id": "req-1"}]},
            {"@id": "dep-req-to-need", "@type": "Dependency",
             "source": [{"@id": "req-unverified"}], "target": [{"@id": "need-1"}]},
        ]
        assert _targets(
            traversal, "hasRelevantEvidenceContract", "req-1", elements
        ) == []
        assert _targets(
            traversal, "hasRelevantEvidenceContract", "need-1", elements
        ) == []

    def test_generic_dependency_never_establishes_the_range(self):
        """The Dependency witness exists and stays visible under its own
        reviewed predicate (hasRelevantArchitecture); it never establishes
        EvidenceContract identity for the blocked range."""
        traversal = _traversal(_kernel_bindings())
        elements = _elements()
        assert _targets(
            traversal, "hasRelevantArchitecture", "req-1", elements
        ) == ["part-plain"]
        assert _targets(
            traversal, "hasRelevantEvidenceContract", "req-1", elements
        ) == []

    def test_non_requirement_usage_source_is_rejected_before_identity(self):
        """The declared source-type filter still applies: a part source is
        never an evidence-contract hop even when something is verified."""
        traversal = _traversal(_kernel_bindings())
        elements = _elements() + [
            {"@id": "part-source", "@type": "PartUsage"},
            {"@id": "dep-part", "@type": "Dependency",
             "source": [{"@id": "part-source"}], "target": [{"@id": "req-1"}]},
        ]
        assert "part-source" not in _targets(
            traversal, "hasRelevantEvidenceContract", "req-1", elements
        )

    def test_range_gate_keys_on_the_governed_contract(self):
        """The identity gate applies to the reviewed EvidenceContract range
        class only; the ontology still declares that range and domain."""
        mapping = _contract().relationship_mapping("hasRelevantEvidenceContract")
        assert mapping.range == "EvidenceContract"
        assert mapping.domain == "Requirement"
        source = TRAVERSAL_SOURCE.read_text(encoding="utf-8")
        assert '_EVIDENCE_CONTRACT_RANGE_CLASS = "EvidenceContract"' in source
        assert "def _evidence_contract_identity_ids(" in source
        assert "def _natively_verified_ids(" in source


class TestDisjointness:
    def test_no_witness_object_carries_two_predicates(self):
        """The relevance family is disjoint by construction: no relationship
        object is reported under two of the four predicates."""
        traversal = _traversal(_kernel_bindings())
        elements = _elements()
        by_id = _by_id(elements)
        witnesses: dict[str, set[str]] = {}
        for predicate, source_id in (
            ("realizedBy", "req-1"),
            ("specifiesFunction", "req-1"),
            ("hasRelevantArchitecture", "req-1"),
            ("hasRelevantEvidenceContract", "req-1"),
        ):
            hops = traversal.traverse(predicate, by_id[source_id], elements)
            witnesses[predicate] = {hop.api_object["@id"] for hop in hops}
        pairs = list(witnesses)
        for index, left in enumerate(pairs):
            for right in pairs[index + 1:]:
                assert witnesses[left] & witnesses[right] == set(), (left, right)

    def test_shared_element_keeps_distinct_roles(self):
        """One element may appear under two queries through DISTINCT objects
        (function target + architecture source) — allowed and reviewed."""
        traversal = _traversal(_kernel_bindings())
        elements = _elements() + [
            {"@id": "dep-arch-back", "@type": "Dependency",
             "source": [{"@id": "action-1"}], "target": [{"@id": "req-1"}]},
        ]
        function_hops = traversal.traverse(
            "specifiesFunction", _by_id(elements)["req-1"], elements
        )
        architecture_hops = traversal.traverse(
            "hasRelevantArchitecture", _by_id(elements)["req-1"], elements
        )
        assert [hop.target["@id"] for hop in function_hops] == ["action-1"]
        assert "action-1" in [hop.target["@id"] for hop in architecture_hops]
        assert function_hops[0].api_object["@id"] == "dep-sf"
        assert {
            hop.api_object["@id"] for hop in architecture_hops
        }.isdisjoint({"dep-sf"})


class TestImpactServiceConsumer:
    def _impact(self, elements, kernel_bindings=None):
        from de4sdv.semantic.api_binding import OntologyApiBinder
        from de4sdv.semantic.impact import ImpactService
        from de4sdv.semantic.traversal import SemanticTraversal
        from de4sdv.semantic.kernel_binding_index import KernelBindingIndex
        from de4sdv.sysml_api.revisions import RevisionBinding

        binding_dict = _binding_dict(
            _kernel_bindings() if kernel_bindings is None else kernel_bindings
        )
        binding = RevisionBinding.from_dict(binding_dict)
        index = KernelBindingIndex.from_binding(binding)
        contract = _contract()

        class _Repo:
            def list_elements(self, project_id, commit_id):
                return elements

        traversal = SemanticTraversal(contract, kernel_bindings=index)
        service = ImpactService(
            repository=_Repo(),  # type: ignore[arg-type]
            binding=binding,
            contract=contract,
            binder=OntologyApiBinder(
                contract,
                _Repo(),  # type: ignore[arg-type]
                project_id="project-1",
                commit_id="commit-1",
                kernel_bindings=index,
            ),
            traversal=traversal,
        )
        return service.impact("req-1", git_revision="a" * 40)

    def test_impact_edges_reflect_the_narrowed_predicates(self):
        result = self._impact(_elements())
        predicates = {edge["predicate"] for edge in result["edges"]}
        assert "specifiesFunction" in predicates
        assert "hasRelevantArchitecture" in predicates
        # The corrected EvidenceContract range emits nothing: no
        # hasRelevantEvidenceContract edge is produced while it is blocked.
        assert "hasRelevantEvidenceContract" not in predicates
        # The unverified requirement-like source never becomes an edge.
        assert all(
            edge["source"] != "req-unverified" and edge["target"] != "req-unverified"
            for edge in result["edges"]
        )
        # The need-sourced allocation never becomes a realizedBy edge.
        assert all(
            edge["predicate"] != "realizedBy" or edge["target"] != "action-1-needs"
            for edge in result["edges"]
        )

    def test_impact_reports_the_blocked_evidence_range(self):
        """No EvidenceContract-labeled node is produced, and the evidence gap
        names the blocked range instead of pretending the dependency is
        missing."""
        result = self._impact(_elements())
        assert all(
            node["semantic_type"] != "EvidenceContract" for node in result["nodes"]
        )
        evidence_gaps = [
            gap for gap in result["gaps"] if gap["category"] == "evidence"
        ]
        assert len(evidence_gaps) == 1
        assert "EvidenceContract range is blocked" in evidence_gaps[0]["reason"]

    def test_impact_gap_labels_stay_bounded(self):
        result = self._impact(_elements())
        gap_categories = {gap["category"] for gap in result["gaps"]}
        # Allocation witness set is inert for the fixture requirement shape
        # used here (the allocation is present, so no architecture gap).
        assert "architecture" not in gap_categories
        assert "function" not in gap_categories
        claims = result["claims"]["dependency_semantics"]
        assert "relevance only" in claims


class TestNoNameHeuristics:
    def test_unverified_source_with_misleading_name_is_rejected(self):
        traversal = _traversal(_kernel_bindings())
        elements = _elements() + [
            {"@id": "ec-lookalike", "@type": "RequirementUsage",
             "declaredName": "evidenceContractFreshOverrideClear"},
            {"@id": "dep-lookalike", "@type": "Dependency",
             "source": [{"@id": "ec-lookalike"}], "target": [{"@id": "req-1"}]},
        ]
        assert "ec-lookalike" not in _targets(
            traversal, "hasRelevantEvidenceContract", "req-1", elements
        )

    def test_verified_source_with_misleading_name_is_still_rejected(self):
        """A name containing 'evidenceContract' WITH a verification
        membership is still not an evidence contract: names never
        participate; the range is blocked and emits nothing."""
        traversal = _traversal(_kernel_bindings())
        elements = _elements() + [
            {"@id": "ec-named", "@type": "RequirementUsage",
             "declaredName": "evidenceContractNamedProbe"},
            {"@id": "rvm-named", "@type": "RequirementVerificationMembership",
             "memberElement": {"@id": "ec-named"}},
            {"@id": "dep-named", "@type": "Dependency",
             "source": [{"@id": "ec-named"}], "target": [{"@id": "req-1"}]},
        ]
        assert "ec-named" in traversal._natively_verified_ids(elements)
        assert "ec-named" not in _targets(
            traversal, "hasRelevantEvidenceContract", "req-1", elements
        )

    def test_part_named_like_the_kernel_is_not_a_requirement_source(self):
        traversal = _traversal(_kernel_bindings())
        elements = _elements() + [
            {"@id": "part-homonym", "@type": "PartUsage",
             "declaredName": "RequirementCandidate"},
            {"@id": "dep-homonym-part", "@type": "Dependency",
             "source": [{"@id": "part-homonym"}], "target": [{"@id": "req-1"}]},
        ]
        # It is a legitimate architecture source (part-typed), never a
        # requirement-domain query source.
        assert "part-homonym" in _targets(
            traversal, "hasRelevantArchitecture", "req-1", elements
        )
        assert _targets(
            traversal, "hasRelevantEvidenceContract", "req-1", elements
        ) == []


class TestReplayEvidence:
    def test_replay_numbers_are_locked_and_consistent(self):
        assert REPLAY_REALIZEDBY_REAL_HOPS == 0
        assert REPLAY_ALLOCATION_OBJECTS == 71
        assert REPLAY_REQUIREMENT_SOURCED_ALLOCATIONS == 10
        assert REPLAY_REALIZEDBY_FUNCTION_LAYER == 10
        assert REPLAY_REALIZEDBY_LOGICAL_LAYER == 0
        assert REPLAY_REALIZEDBY_PHYSICAL_LAYER == 0
        assert REPLAY_REALIZEDBY_OTHER_LAYER == 0
        assert REPLAY_REALIZEDBY_INVALID == 0
        assert REPLAY_SPECIFIESFUNCTION_HOPS == 16
        assert REPLAY_SPECIFIESFUNCTION_SOURCES == 15
        assert REPLAY_HRA_PRE == REPLAY_HRA_POST + REPLAY_HRA_REJECTED
        assert REPLAY_HRA_PRE == 143 and REPLAY_HRA_POST == 42
        # hasRelevantEvidenceContract correction accounting: pre-c5 140 hops
        # over 90 sources; requirement-queried hops = 89 domain rejections +
        # 51 candidate evaluations; the rejected over-broad execution emitted
        # 34 hops over 29 distinct sources (16 acceptance-criterion-role
        # over 14 sources + 18 unproven over 15 sources); the corrected gate
        # emits 0.
        assert REPLAY_HEC_PRE == 140
        assert REPLAY_HEC_PRE == REPLAY_HEC_REJECTED_QUERY_DOMAIN + REPLAY_HEC_REQUIREMENT_QUERIED
        assert REPLAY_HEC_REQUIREMENT_QUERIED == 51
        assert REPLAY_HEC_REQUIREMENT_QUERIED == (
            REPLAY_HEC_REQUIREMENT_QUERIED_UNVERIFIED
            + REPLAY_HEC_ACCEPTANCE_CRITERION_HOPS
            + REPLAY_HEC_UNRESOLVED_AMBIGUOUS_HOPS
            + REPLAY_HEC_ORDINARY_VERIFIED_HOPS
        )
        assert REPLAY_HEC_ACCEPTANCE_CRITERION_HOPS == 16
        assert REPLAY_HEC_UNRESOLVED_AMBIGUOUS_HOPS == 18
        assert REPLAY_HEC_ACCEPTANCE_CRITERION_SOURCES == 14
        assert REPLAY_HEC_UNRESOLVED_AMBIGUOUS_SOURCES == 15
        assert REPLAY_HEC_EXECUTED_C5 == (
            REPLAY_HEC_ACCEPTANCE_CRITERION_HOPS + REPLAY_HEC_UNRESOLVED_AMBIGUOUS_HOPS
        )
        assert REPLAY_HEC_EXECUTED_C5_SOURCES == (
            REPLAY_HEC_ACCEPTANCE_CRITERION_SOURCES
            + REPLAY_HEC_UNRESOLVED_AMBIGUOUS_SOURCES
        )
        assert REPLAY_HEC_UNRESOLVED_CANDIDATE_SOURCES == 16
        assert REPLAY_HEC_PRE_SOURCES == (
            REPLAY_HEC_ACCEPTANCE_CRITERION_SOURCES
            + REPLAY_HEC_UNRESOLVED_CANDIDATE_SOURCES
            + REPLAY_HEC_REJECTED_UNVERIFIED_SOURCES
            + REPLAY_HEC_NEED_SOURCES
        )
        assert REPLAY_HEC_CORRECTED == 0
        assert REPLAY_HEC_CORRECTED_SOURCES == 0

    def test_replay_numbers_are_recorded_in_the_decisions_and_review_doc(
        self, decisions
    ):
        doc = _review_text()
        for token in ("143", "101", "42", "140", "89", "34", "16", "18"):
            assert token in doc, token
        realized = _decision_text(decisions["entries"]["realizedBy"])
        assert "71" in realized and "10 Function / 0 LogicalElement" in realized
        architecture = _decision_text(
            decisions["entries"]["hasRelevantArchitecture"]
        )
        assert "143" in architecture and "101" in architecture and "42" in architecture
        evidence = _decision_text(
            decisions["entries"]["hasRelevantEvidenceContract"]
        )
        assert "140" in evidence and "34" in evidence and "0 hops over 0 sources" in evidence

    def test_retained_evidence_is_supporting_only(self):
        doc = _review_text()
        assert "0a23902370de9fc74d6118afe480382e0b0d8aa0" in doc
        assert "34576049742" in doc
        assert "10195168006" in doc
        assert (
            "sha256:e1c13b2e9d525dadddf4e861b52035e05252c7079b0e6ac989c7fef702a1718d"
            in doc
        )
        assert "supporting evidence only" in doc
        assert "not current-head privileged closure" in doc

    def test_no_privileged_ingestion_dispatched(self):
        doc = _review_text()
        assert "No privileged ingestion was dispatched for c5" in doc


class TestDocumentAndBoundaryLaws:
    def test_review_doc_exists_and_names_the_decisions(self):
        text = _review_text()
        for fragment in (
            "Outcome D",
            "Outcome B",
            "rename/replacement required",
            "not the canonical RFLP realization chain",
            "a query shortcut is not automatically a new engineering fact",
            "10 Function / 0 LogicalElement / 0 PhysicalElement / 0 other",
            "zero hops against the real serialized model",
            "RequirementVerificationMembership",
            "kernel rule",
            "disjoint",
            "No `.sysml` file changed",
            "No privileged ingestion was dispatched for c5",
            "The c4 retirement remains intact",
            "allocatedTo",
            "deployedTo",
            "untouched",
            # c5 correction fragments (whitespace-normalized doc text):
            "c5 correction (independent review, this revision)",
            "machine-resolvable, non-heuristic `EvidenceContract` discriminator",
            "Exact blocker:",
            "native verification membership also admits AcceptanceCriterion",
            "Verification association vs identity",
            "not emitted as evidence-contract hops under",
            "no returned target without proven `EvidenceContract` identity",
        ):
            assert fragment in text, fragment

    def test_review_doc_records_c5a_c5b_split_and_non_claims(self):
        text = _review_text()
        assert "c5a" in text and "c5b" in text
        assert "explicitly distinguished and not interchangeable" in text
        assert "No composite realization query exists" in text

    def test_no_sysml_or_ontology_semantic_change_by_this_batch(self):
        """The four authored contracts are byte-stable in c5: no predicate
        name/signature/config change, no allocatedTo/deployedTo touch."""
        ontology = yaml.safe_load(ONTOLOGY_PATH.read_text(encoding="utf-8"))
        relationships = ontology["relationships"]
        assert len(relationships) == 34
        assert relationships["realizedBy"]["sysml_mapping"] == {
            "strategy": "allocation",
            "relationship_types": ["AllocationUsage"],
            "direction": "outgoing",
            "source_property": "source",
            "target_property": "target",
            "semantic_strength": "allocation",
        }
        assert relationships["specifiesFunction"]["sysml_mapping"] == {
            "strategy": "dependency",
            "relationship_types": ["Dependency"],
            "direction": "outgoing",
            "source_property": "source",
            "target_property": "target",
            "source_types": ["RequirementUsage"],
            "target_types": ["ActionUsage", "ActionDefinition"],
            "semantic_strength": "relevance",
        }
        assert relationships["hasRelevantArchitecture"]["sysml_mapping"] == {
            "strategy": "dependency",
            "relationship_types": ["Dependency"],
            "direction": "incoming",
            "source_property": "source",
            "target_property": "target",
            "source_types": [
                "PartUsage",
                "PartDefinition",
                "ActionUsage",
                "ActionDefinition",
            ],
            "exclude_source_specializations_of": "MemberProduct",
            "semantic_strength": "relevance",
        }
        assert relationships["hasRelevantEvidenceContract"]["sysml_mapping"] == {
            "strategy": "dependency",
            "relationship_types": ["Dependency"],
            "direction": "incoming",
            "source_property": "source",
            "target_property": "target",
            "source_types": ["RequirementUsage"],
            "semantic_strength": "relevance",
        }
        assert set(relationships["allocatedTo"]) == {"domain", "range"}
        assert relationships["allocatedTo"]["domain"] == "Function"
        assert relationships["allocatedTo"]["range"] == "LogicalElement"
        assert set(relationships["deployedTo"]) == {"domain", "range"}
        assert relationships["deployedTo"]["domain"] == "LogicalElement"
        assert relationships["deployedTo"]["range"] == "PhysicalElement"

    def test_c4_retirement_mechanics_unchanged(self):
        source = TRAVERSAL_SOURCE.read_text(encoding="utf-8")
        assert "derivesNeedFromConcern" not in source
        ontology = yaml.safe_load(ONTOLOGY_PATH.read_text(encoding="utf-8"))
        assert "sysml_mapping" not in ontology["relationships"]["derivesNeedFromConcern"]
        assert "sysml_mapping" not in ontology["relationships"]["addressesConcern"]

    def test_runtime_does_not_read_the_inventory(self):
        assert "NEVER imported by the semantic runtime" in (ai.__doc__ or "")
        source = TRAVERSAL_SOURCE.read_text(encoding="utf-8")
        assert "authority_inventory" not in source
        assert "semantic-authority-inventory" not in source

    def test_no_source_text_parsing_in_traversal(self):
        source = TRAVERSAL_SOURCE.read_text(encoding="utf-8")
        for banned in ("read_text(", "rglob", "open(", "Path("):
            assert banned not in source, banned

    def test_inventory_row_is_consistent_with_the_decisions_row(
        self, inventory, decisions
    ):
        """The generated artifact must reproduce the reviewed decision rows
        (governance consistency; red between Commit A and Commit B by design)."""
        entries = _entries(inventory)
        for identity in C5_IDENTITIES:
            reviewed = entries[identity]["reviewed"]
            source = decisions["entries"][identity]
            for field in (
                "authority_current",
                "authority_target",
                "disposition",
                "evidence_state",
                "conditional_target",
                "transition_gate",
                "unknowns",
                "required_evidence",
                "exact_fit_decision",
                "stage",
                "confidence",
            ):
                assert reviewed[field] == source[field], (identity, field)

    def test_no_conditional_and_no_closure_evidence_for_c5(self, inventory):
        entries = _entries(inventory)
        for identity in C5_IDENTITIES:
            row = entries[identity]["reviewed"]
            assert row["conditional_target"] is False, identity
            assert row["closure_evidence_ref"] is None, identity
        for identity in C5_PARITY_ROWS:
            row = entries[identity]["reviewed"]
            assert row["evidence_state"] not in {
                "blocked",
                "unknown",
                "privileged-closure-proven",
                "exact-toolchain-validated",
            }, identity
        assert (
            entries["hasRelevantEvidenceContract"]["reviewed"]["evidence_state"]
            == "blocked"
        )








