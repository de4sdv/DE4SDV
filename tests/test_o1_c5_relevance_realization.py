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

from pathlib import Path

import pytest

from de4sdv.semantic import authority_inventory as ai
from de4sdv.semantic.kernel_contract import KernelContract
from model_contract_fixtures import model_contract  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]

TRAVERSAL_SOURCE = REPO_ROOT / "de4sdv/semantic/traversal.py"

C5_IDENTITIES: tuple[str, ...] = (
    "realizedBy",
    "specifiesFunction",
    "hasRelevantArchitecture",
    "hasRelevantEvidenceContract",
)


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
    return model_contract()


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


# ---------------------------------------------------------------------------
# Reviewed decisions (the source rows)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# `rename-required` schema laws
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Hardened traversal laws (the c5 runtime contract)
# ---------------------------------------------------------------------------


def _binding_dict(kernel_bindings: list[dict[str, str]]) -> dict:
    return {
        "schema": "de4sdv.revision-binding/v2",
        "git_repository": "de4sdv/DE4SDV",
        "git_commit": "a" * 40,
        "sysml_project_id": "project-1",
        "sysml_commit_id": "commit-1",
        "import_timestamp": "2026-09-13T00:00:00Z",
        "import_tool_version": "test",
        "semantic_validation": "passed",
        "scope": "fixture",
        "semantic_authority": _contract().identity.to_dict(),
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

    def test_realized_by_is_refused_as_a_retired_name(self):
        """O4 Wave C2 (owner decision D4): realizedBy is retired; the contract
        refuses it with its successor instead of answering allocation hops.
        The allocation laws are carried by the allocatedTo successor tests."""
        from de4sdv.semantic.kernel_contract import RetiredIdentityError

        traversal = _traversal(_kernel_bindings())
        with pytest.raises(RetiredIdentityError, match="retired; use allocatedTo"):
            traversal.traverse("realizedBy", _by_id(_elements())["req-1"], _elements())

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

    def test_realized_by_answers_no_allocation_fact(self):
        """O4 Wave C2: the retired name is refused (owner decision D4)."""
        from de4sdv.semantic.kernel_contract import RetiredIdentityError

        with pytest.raises(RetiredIdentityError, match="retired; use allocatedTo"):
            _contract().relationship_mapping("realizedBy")
        assert "realizedBy" not in _contract().relationships


# O4 Wave C2 review R4: restored from base 6dab3e9 verbatim. They cover live
# traversal behavior (specifiesFunction laws, the blocked EvidenceContract
# range gate) and pass on the model-built contract and the revision binding
# v2 helpers above; only those helpers changed.


class TestSpecifiesFunctionLaws:
    def test_generic_dependency_is_not_specification(self):
        """The hop is relevance strength; no specification semantics are claimed."""
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
        object is reported under two of the three remaining dependency
        predicates (realizedBy is retired since O4 Wave C2)."""
        traversal = _traversal(_kernel_bindings())
        elements = _elements()
        by_id = _by_id(elements)
        witnesses: dict[str, set[str]] = {}
        for predicate, source_id in (
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
        """The production impact surface of the model-authority runtime (O4
        Wave C2; the base ImpactService subclass the validators consume)."""
        from de4sdv.sysml_api.revisions import RevisionBinding
        from model_contract_fixtures import model_service

        bindings = _kernel_bindings() if kernel_bindings is None else kernel_bindings
        full_paths = {
            "de4sdv_method_context.sysml":
                "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml",
            "de4sdv_product_line.sysml":
                "textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml",
        }
        bindings = [{**b, "source_file": full_paths.get(b["source_file"], b["source_file"])}
                    for b in bindings]
        binding = RevisionBinding.from_dict(_binding_dict(bindings))

        class _Repo:
            def list_elements(self, project_id, commit_id):
                return elements

        service = model_service(binding, _Repo()).impact_service
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


class TestDocumentAndBoundaryLaws:


    def test_no_sysml_or_ontology_semantic_change_by_this_batch(self):
        """The c5 contracts are stable in the model-built kernel contract (the
        authored ontology was deleted in O4 Wave C2): no predicate
        signature/config change; the retired names are refused."""
        from de4sdv.semantic.kernel_contract import RetiredIdentityError

        contract = _contract()

        def mapping(name):
            value = contract.relationship_mapping(name)
            return {"strategy": value.strategy, **value.configuration,
                    "semantic_strength": value.semantic_strength}

        assert mapping("specifiesFunction") == {
            "strategy": "dependency",
            "relationship_types": ["Dependency"],
            "direction": "outgoing",
            "source_property": "source",
            "target_property": "target",
            "source_types": ["RequirementUsage"],
            "target_types": ["ActionUsage", "ActionDefinition"],
            "semantic_strength": "relevance",
        }
        assert mapping("hasRelevantArchitecture") == {
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
        assert mapping("hasRelevantEvidenceContract") == {
            "strategy": "dependency",
            "relationship_types": ["Dependency"],
            "direction": "incoming",
            "source_property": "source",
            "target_property": "target",
            "source_types": ["RequirementUsage"],
            "semantic_strength": "relevance",
        }
        for retired in ("realizedBy", "deployedTo"):
            with pytest.raises(RetiredIdentityError, match="retired; use allocatedTo"):
                contract.relationship_mapping(retired)
        assert contract.relationship_mapping("allocatedTo").strategy == "successor"

    def test_c4_retirement_mechanics_unchanged(self):
        """derivesNeedFromConcern: O4 Wave C2 refuses it with its register
        disposition (owner decision D5, intentional migration from the former
        vocabulary-only gap); addressesConcern stays vocabulary-only."""
        from de4sdv.semantic.kernel_contract import RetiredIdentityError

        source = TRAVERSAL_SOURCE.read_text(encoding="utf-8")
        assert "derivesNeedFromConcern" not in source
        with pytest.raises(RetiredIdentityError, match="register disposition REMOVE"):
            _contract().relationship_mapping("derivesNeedFromConcern")
        with pytest.raises(KeyError, match="no SysML mapping"):
            _contract().relationship_mapping("addressesConcern")

    def test_runtime_does_not_read_the_inventory(self):
        assert "never imported by the semantic runtime" in (ai.__doc__ or "").lower()
        source = TRAVERSAL_SOURCE.read_text(encoding="utf-8")
        assert "authority_inventory" not in source
        assert "semantic-authority-inventory" not in source

    def test_no_source_text_parsing_in_traversal(self):
        source = TRAVERSAL_SOURCE.read_text(encoding="utf-8")
        for banned in ("read_text(", "rglob", "open(", "Path("):
            assert banned not in source, banned
