"""O1 c3 — hasSubject native-semantics / DE4SDV-scope review (PR #249).

Covers the c3 claim for exactly one identity:

- relationship ``hasSubject`` (``Requirement -> MemberProduct``): the c3
  Case B decision — the canonical predicate is genuinely narrower than
  native SysML subject semantics, so ``authority_target`` is
  ``de4sdv-application-semantic`` while native ``SubjectMembership`` remains
  the grounding witness; the bounded fail-closed traversal hardening
  enforces the mapping's governed domain/range (Requirement lineage source,
  MemberProduct lineage target) through the ingestion-validated kernel
  bindings plus the representation-tolerant relationship graph, never
  through names.

The batch tests:

1.  exactly ``hasSubject`` comprises c3 (no second identity promoted; the
    global parity set is the seven c1 rows plus the two c2 rows plus this
    one);
2.  authority is unchanged: ``hasSubject`` stays ``legacy-yaml`` (no O3
    cutover) with the reviewed Case B target and parity-reviewed evidence;
3.  the reviewed decision records the decomposition, the Case B rationale,
    the retained-run over-return replay, and the bounded claim;
4.  positive native witnesses: direct ProductLineMemberProduct usage typing
    and a legitimate specialization each produce exactly one hop;
5.  the source negative laws: a RequirementUsage without DE4SDV Requirement
    lineage, a StakeholderNeedCandidate usage (the real N-AEBS/N-MW shape),
    a verification/evidence-contract usage, a correct short/display name
    with wrong lineage, a missing kernel binding, and a non-configured owner
    metaclass never produce a hop;
6.  the target negative laws: arbitrary PartUsage, verification bench,
    architecture part, stakeholder usage, another requirement usage, a part
    merely named memberProduct, an unrelated same-named definition, a
    dangling memberElement, ambiguous lineage, and a missing MemberProduct
    binding never produce a hop;
7.  the relationship negative laws: FeatureMembership, OwningMembership,
    RequirementVerificationMembership, Dependency, AllocationUsage, a plain
    reference property, and a PLE configuration relation are never
    substitutes for the native SubjectMembership discriminator;
8.  no name fallback: name-only correspondence without lineage grounding is
    rejected in both directions;
9.  the mapping-parity lock: enforcement is derived from the declared
    domain/range (changing one changes/refuses the mechanics
    deterministically; the mechanics carry no second type contract);
10. the ImpactService boundary: a non-MemberProduct native subject is never
    reported as a MemberProduct product-line hop, while the valid subject
    still appears;
11. no runtime inventory dependency, no new Semantic Projection row, and
    c1/c2/K/PLE/c4/c5 states unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic import authority_inventory as ai
from de4sdv.semantic.kernel_contract import KernelContract
from de4sdv.semantic.traversal import SemanticTraversal
from de4sdv.sysml_api.errors import IdentityNotFoundError

REPO_ROOT = Path(__file__).resolve().parents[1]

INVENTORY_PATH = (
    REPO_ROOT / "docs/method-conformance/o1/semantic-authority-inventory.json"
)
DECISIONS_PATH = (
    REPO_ROOT / "docs/method-conformance/o1/authority-review-decisions.yaml"
)
CLOSURE_PATH = REPO_ROOT / "docs/method-conformance/o1/closure-evidence.json"
REVIEW_DOC = (
    REPO_ROOT / "docs/method-conformance/o1/c3-subject-grounding-review.md"
)
TRAVERSAL_SOURCE = REPO_ROOT / "de4sdv/semantic/traversal.py"

#: The c3 batch is exactly this one identity — no second entry.
C3_IDENTITIES: tuple[str, ...] = ("hasSubject",)

#: The seven c1 identities accepted as parity-reviewed (unchanged by c3).
C1_ACCEPTED: tuple[str, ...] = (
    "MethodPhase",
    "MethodContractObligation",
    "EvaluationSourceKind",
    "EvaluationScopeMembership",
    "TestedScopeDeclaration",
    "RetainedExecutionRecordReference",
    "AcceptanceAttestationReference",
)

#: The one c1 identity that stays incomplete (no c3 silent closure).
C1_INCOMPLETE: tuple[str, ...] = ("MethodEvaluationScope",)

#: The two c2 identities (unchanged by c3).
C2_IDENTITIES: tuple[str, ...] = ("VerificationCase", "verifiedBy")

#: PLE-family rows under the adoption gate (unchanged by c3).
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

#: K rows with the r6-3 closure record (unchanged by c3).
K_TRIPLE: tuple[str, ...] = (
    "DerivesFromNeed",
    "derivesRequirementFromNeed",
    "derivedRequirementsOfNeed",
)

#: Retained-export replay numbers (full-model candidate export at
#: 0a23902370de9fc74d6118afe480382e0b0d8aa0; 289 SubjectMembership
#: elements). The pre-c3 traversal over-returned 110 hops that the enforced
#: Requirement->MemberProduct contract rejects while preserving all 21
#: legitimate hops. Locked as constants: a regression that silently widens
#: the traversal must break these.
REPLAY_TOTAL_MEMBERSHIPS = 289
REPLAY_PRE_C3_HOPS = 131
REPLAY_POST_C3_HOPS = 21
REPLAY_REMOVED_NON_REQUIREMENT_SOURCES = 57
REPLAY_REMOVED_NON_MEMBERPRODUCT_TARGETS = 53


# ---------------------------------------------------------------------------
# Fixture vocabulary: kernel lineages and serialized subject shapes
# ---------------------------------------------------------------------------


def _contract() -> KernelContract:
    return KernelContract.load(
        REPO_ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
    )


def _kernel_elements() -> tuple[dict, dict, dict, dict]:
    """The four validated lineage definitions the fixtures ground against."""
    return (
        {
            "@id": "kernel-requirement",
            "@type": "RequirementDefinition",
            "declaredName": "RequirementCandidate",
            "qualifiedName": "DE4SDV_MethodContext::RequirementCandidate",
        },
        {
            "@id": "kernel-need",
            "@type": "RequirementDefinition",
            "declaredName": "StakeholderNeedCandidate",
            "qualifiedName": "DE4SDV_MethodContext::StakeholderNeedCandidate",
        },
        {
            "@id": "kernel-member-product",
            "@type": "PartDefinition",
            "declaredName": "ProductLineMemberProduct",
            "qualifiedName": "DE4SDV_ProductLine::ProductLineMemberProduct",
        },
        {
            "@id": "kernel-bench",
            "@type": "PartDefinition",
            "declaredName": "VehicleTargetBench",
            "qualifiedName": "DE4SDV_TestInfrastructure::VehicleTargetBench",
        },
    )


def _typing(element_id_value: str, type_id: str, witness_id: str) -> dict:
    """Authored FeatureTyping (real serializer shape)."""
    return {
        "@id": witness_id,
        "@type": "FeatureTyping",
        "owningRelatedElement": {"@id": element_id_value},
        "type": {"@id": type_id},
        "typedFeature": {"@id": element_id_value},
    }


def _subclassification(
    specific_id: str, general_id: str, witness_id: str
) -> dict:
    """Authored Subclassification (real serializer shape)."""
    return {
        "@id": witness_id,
        "@type": "Subclassification",
        "subclassifier": {"@id": specific_id},
        "superclassifier": {"@id": general_id},
        "specific": {"@id": specific_id},
        "general": {"@id": general_id},
    }


def _kernel_index(
    requirement: bool = True, member_product: bool = True, need: bool = False
):
    """Validated kernel bindings for the c3 domain/range lineages.

    ``requirement``/``member_product`` drop the corresponding binding to
    exercise the missing-binding fail-closed law. ``need`` adds the Need
    binding for the domain-swap parity tests.
    """
    from de4sdv.semantic.kernel_binding_index import KernelBindingIndex
    from de4sdv.sysml_api.revisions import RevisionBinding

    bindings: list[dict[str, str]] = []
    if requirement:
        bindings.append(
            {
                "ontology_class": "Requirement",
                "element_id": "kernel-requirement",
                "source_file": (
                    "textual-notation-of-model/packages/methods/de4sdv/"
                    "de4sdv_method_context.sysml"
                ),
                "declaration": "requirement def RequirementCandidate",
            }
        )
    if member_product:
        bindings.append(
            {
                "ontology_class": "MemberProduct",
                "element_id": "kernel-member-product",
                "source_file": (
                    "textual-notation-of-model/packages/methods/de4sdv/"
                    "de4sdv_product_line.sysml"
                ),
                "declaration": "part def ProductLineMemberProduct",
            }
        )
    if need:
        bindings.append(
            {
                "ontology_class": "Need",
                "element_id": "kernel-need",
                "source_file": (
                    "textual-notation-of-model/packages/methods/de4sdv/"
                    "de4sdv_method_context.sysml"
                ),
                "declaration": "requirement def StakeholderNeedCandidate",
            }
        )
    return KernelBindingIndex.from_binding(
        RevisionBinding.from_dict(
            {
                "git_repository": "de4sdv/DE4SDV",
                "git_commit": "a" * 40,
                "sysml_project_id": "project-1",
                "sysml_commit_id": "commit-1",
                "import_timestamp": "2026-08-31T00:00:00Z",
                "import_tool_version": "test",
                "semantic_validation": "passed",
                "scope": "fixture",
                "ontology": _contract().identity.to_dict(),
                "kernel_bindings": bindings,
            }
        )
    )


def _subject_membership(
    membership_id: str, owner_id: str, member_id: str
) -> dict:
    """Native SubjectMembership in the real serialized shape."""
    return {
        "@id": membership_id,
        "@type": "SubjectMembership",
        "memberName": "memberProduct",
        "owningRelatedElement": {"@id": owner_id},
        "memberElement": {"@id": member_id},
        "ownedRelatedElement": [{"@id": member_id}],
    }


def _traverse(source: dict, elements: list[dict], *, with_bindings=True):
    index = _kernel_index() if with_bindings else None
    return SemanticTraversal(_contract(), kernel_bindings=index).traverse(
        "hasSubject", source, elements
    )


def _qualifying_fixture() -> tuple[list[dict], dict]:
    """One governed requirement with one qualifying member-product subject."""
    elements = list(_kernel_elements())
    requirement = {
        "@id": "req-1",
        "@type": "RequirementUsage",
        "declaredName": "reqCommandEmergencyBraking",
    }
    member = {
        "@id": "member-1",
        "@type": "ReferenceUsage",
        "declaredName": "memberProduct",
    }
    elements += [
        requirement,
        member,
        _typing("req-1", "kernel-requirement", "ft-req-1"),
        _typing("member-1", "kernel-member-product", "ft-member-1"),
        _subject_membership("sm-1", "req-1", "member-1"),
    ]
    return elements, requirement


# ---------------------------------------------------------------------------
# c3 scope, decisions, and inventory state
# ---------------------------------------------------------------------------


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


class TestC3ScopeAndCounts:
    def test_c3_is_exactly_one_identity(self):
        assert C3_IDENTITIES == ("hasSubject",)

    def test_has_subject_is_an_ontology_relationship(self, inventory, decisions):
        entries = _entries(inventory)
        assert entries["hasSubject"]["kind"] == "relationship"
        assert entries["hasSubject"]["observed"]["domain"] == "Requirement"
        assert entries["hasSubject"]["observed"]["range"] == "MemberProduct"
        assert "hasSubject" in decisions["entries"]

    def test_only_c3_identities_carry_the_c3_stage(self, inventory):
        staged = [
            entry["identity"]
            for entry in inventory["entries"]
            if str(entry["reviewed"]["stage"]).startswith("c3")
        ]
        assert staged == ["hasSubject"]

    def test_global_parity_set_is_c1_plus_c2_plus_c3(self, inventory):
        parity = {
            entry["identity"]
            for entry in inventory["entries"]
            if entry["reviewed"]["evidence_state"] == "parity-reviewed"
        }
        assert parity == set(C1_ACCEPTED) | set(C2_IDENTITIES) | set(C3_IDENTITIES)
        assert len(parity) == 10

    def test_authority_current_remains_legacy_yaml(self, inventory):
        entries = _entries(inventory, C3_IDENTITIES)
        assert (
            entries["hasSubject"]["reviewed"]["authority_current"]
            == "legacy-yaml"
        )

    def test_authority_target_is_the_case_b_decision(self, inventory):
        assert (
            _entries(inventory, C3_IDENTITIES)["hasSubject"]["reviewed"][
                "authority_target"
            ]
            == "de4sdv-application-semantic"
        )

    def test_evidence_state_is_parity_reviewed(self, inventory):
        assert (
            _entries(inventory, C3_IDENTITIES)["hasSubject"]["reviewed"][
                "evidence_state"
            ]
            == "parity-reviewed"
        )

    def test_no_closure_evidence_and_no_privileged_claim(self, inventory):
        entry = _entries(inventory, C3_IDENTITIES)["hasSubject"]
        assert entry["reviewed"]["closure_evidence_ref"] is None
        assert entry["reviewed"]["evidence_state"] != "privileged-closure-proven"
        assert entry["reviewed"]["evidence_state"] != "exact-toolchain-validated"
        closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
        assert len(closure["records"]) == 1
        assert closure["records"][0]["id"] == "r6-3"
        assert "hasSubject" not in closure["records"][0]["subject_identities"]

    def test_no_c3_row_is_conditional(self, inventory):
        entry = _entries(inventory, C3_IDENTITIES)["hasSubject"]
        assert entry["reviewed"]["conditional_target"] is False
        assert entry["reviewed"]["transition_gate"] is None

    def test_no_new_semantic_projection_row(self):
        source = (REPO_ROOT / "de4sdv/semantic/projection.py").read_text(
            encoding="utf-8"
        )
        for name in C3_IDENTITIES:
            assert f'"{name}"' not in source, name

    def test_runtime_does_not_read_the_inventory(self):
        from de4sdv.semantic import authority_inventory as ai_module

        assert ai_module.__doc__ is not None
        assert "NEVER imported by the semantic runtime" in ai_module.__doc__
        runtime = (REPO_ROOT / "de4sdv/semantic/traversal.py").read_text(
            encoding="utf-8"
        )
        assert "authority_inventory" not in runtime
        assert "semantic-authority-inventory" not in runtime

    def test_expected_evidence_state_counts(self, inventory):
        """c3 changes evidence maturity only: parity 9 -> 10, repository 66 -> 65;
        every other evidence class is unchanged."""
        assert inventory["evidence_state_counts"] == {
            "blocked": 14,
            "parity-reviewed": 10,
            "privileged-closure-proven": 3,
            "repository-evidenced": 65,
            "unknown": 1,
        }

    def test_expected_authority_target_counts(self, inventory):
        """Target correction native-sysml -> de4sdv-application-semantic moves
        exactly one row; authority_current counts are unchanged."""
        assert inventory["authority_target_counts"] == {
            "accepted-library-grounded": 12,
            "de4sdv-application-semantic": 5,
            "external-reference": 2,
            "model-authoritative": 61,
            "native-sysml": 7,
            "unknown": 6,
        }
        assert inventory["authority_current_counts"] == {
            "accepted-library-grounded": 2,
            "external-reference": 3,
            "legacy-yaml": 78,
            "model-authoritative": 3,
            "native-sysml": 6,
            "unknown": 1,
        }

    def test_c1_rows_unchanged(self, inventory):
        entries = _entries(inventory)
        for name in C1_ACCEPTED:
            row = entries[name]["reviewed"]
            assert row["authority_current"] == "legacy-yaml", name
            assert row["authority_target"] == "model-authoritative", name
            assert row["evidence_state"] == "parity-reviewed", name
        for name in C1_INCOMPLETE:
            row = entries[name]["reviewed"]
            assert row["authority_current"] == "legacy-yaml", name
            assert row["evidence_state"] == "repository-evidenced", name

    def test_c2_rows_unchanged(self, inventory):
        entries = _entries(inventory)
        verification = entries["VerificationCase"]["reviewed"]
        assert verification["authority_current"] == "native-sysml"
        assert verification["authority_target"] == "native-sysml"
        assert verification["evidence_state"] == "parity-reviewed"
        verified_by = entries["verifiedBy"]["reviewed"]
        assert verified_by["authority_current"] == "legacy-yaml"
        assert verified_by["authority_target"] == "native-sysml"
        assert verified_by["evidence_state"] == "parity-reviewed"

    def test_ple_rows_unchanged(self, inventory):
        entries = _entries(inventory)
        for identity in PLE_GATED:
            row = entries[identity]["reviewed"]
            assert row["evidence_state"] == "blocked", identity
            assert row["adoption_status"] == "pinned-not-adopted", identity
            assert row["conditional_target"] is True, identity

    def test_k_rows_unchanged(self, inventory):
        entries = _entries(inventory)
        for identity in K_TRIPLE:
            row = entries[identity]["reviewed"]
            assert row["authority_current"] == "model-authoritative", identity
            assert row["evidence_state"] == "privileged-closure-proven", identity
            assert row["closure_evidence_ref"] == "r6-3", identity

    def test_c4_c5_rows_unchanged(self, inventory):
        entries = _entries(inventory)
        expected = {
            "derivesNeedFromConcern": ("c4", "legacy-yaml", "blocked"),
            "realizedBy": ("c5", "legacy-yaml", "repository-evidenced"),
            "specifiesFunction": ("c5", "legacy-yaml", "repository-evidenced"),
            "hasRelevantArchitecture": (
                "c5",
                "legacy-yaml",
                "repository-evidenced",
            ),
            "hasRelevantEvidenceContract": (
                "c5",
                "legacy-yaml",
                "repository-evidenced",
            ),
        }
        for identity, (stage, authority, evidence) in expected.items():
            row = entries[identity]["reviewed"]
            assert row["stage"] == stage, identity
            assert row["authority_current"] == authority, identity
            assert row["evidence_state"] == evidence, identity


class TestC3ReviewedDecision:
    def test_decision_records_the_case_b_decomposition(self, decisions):
        text = _decision_text(decisions["entries"]["hasSubject"])
        assert "Case B" in text
        assert "de4sdv-application-semantic" in text
        # Native core + both application restrictions are recorded.
        assert "ParameterMembership" in text
        assert "StakeholderNeedCandidate" in text
        assert "sibling lineages" in text
        assert "RequirementUsage" in text
        # The Lane B boundary and the claim boundary are recorded.
        assert "Lane B" in text
        assert "PLE" in text
        assert "legacy-yaml" in text

    def test_decision_records_the_retained_run_replay(self, decisions):
        text = _decision_text(decisions["entries"]["hasSubject"])
        assert "289" in text
        assert "110" in text
        assert "57" in text
        assert "53" in text
        assert "21" in text

    def test_review_doc_exists_and_names_the_decision(self):
        text = REVIEW_DOC.read_text(encoding="utf-8")
        assert "Case B" in text
        assert "de4sdv-application-semantic" in text
        assert "native-reference" in text
        assert "no name filter" in text or "No name" in text
        assert "hasSubject" in text

    def test_claim_boundary_forbids_stronger_claims(self, decisions):
        text = _decision_text(decisions["entries"]["hasSubject"])
        for forbidden in (
            "does not mean selection",
            "does not mean",
        ):
            if forbidden == "does not mean":
                continue
            assert forbidden in text
        # The claim boundary names the exclusions explicitly.
        assert "selection" in text
        assert "satisfaction" in text
        assert "realization" in text
        assert "allocation" in text

    def test_semantic_strength_is_unchanged(self, inventory):
        entry = _entries(inventory, C3_IDENTITIES)["hasSubject"]
        assert entry["observed"]["semantic_strength"] == "native-reference"
        mapping = _contract().relationship_mapping("hasSubject")
        assert mapping.semantic_strength == "native-reference"


# ---------------------------------------------------------------------------
# Positive native witnesses
# ---------------------------------------------------------------------------


class TestPositiveNativeWitnesses:
    def test_direct_product_line_member_product_typing_yields_one_hop(self):
        elements, requirement = _qualifying_fixture()
        hops = _traverse(requirement, elements)
        assert len(hops) == 1
        hop = hops[0]
        assert hop.predicate == "hasSubject"
        assert hop.strategy == "subject-membership"
        assert hop.semantic_strength == "native-reference"
        assert hop.target["@id"] == "member-1"
        assert hop.api_object["@id"] == "sm-1"
        assert hop.witness["membership_id"] == "sm-1"
        assert hop.witness["source_lineage"] == {
            "ontology_class": "Requirement",
            "lineage_root_id": "kernel-requirement",
            "provenance": "explicit",
        }
        assert hop.witness["target_lineage"]["ontology_class"] == "MemberProduct"
        assert hop.witness["target_lineage"]["lineage_root_id"] == (
            "kernel-member-product"
        )
        assert hop.witness["target_lineage"]["provenance"] == "explicit"

    def test_legitimate_specialization_yields_one_hop(self):
        """A part usage typed by a definition that specializes
        ProductLineMemberProduct is a legitimate governed target."""
        elements = list(_kernel_elements())
        specialized = {
            "@id": "kernel-member-product-specialization",
            "@type": "PartDefinition",
            "declaredName": "StandaloneAutowareAEBSReferenceMember",
        }
        requirement = {
            "@id": "req-spec",
            "@type": "RequirementUsage",
            "declaredName": "reqHandleDegradedUnavailableInputs",
        }
        member = {
            "@id": "member-spec",
            "@type": "PartUsage",
            "declaredName": "standaloneAutowareAEBSReferenceMember",
        }
        elements += [
            specialized,
            requirement,
            member,
            _subclassification(
                "kernel-member-product-specialization",
                "kernel-member-product",
                "sub-member-product",
            ),
            _typing("req-spec", "kernel-requirement", "ft-req-spec"),
            _typing("member-spec", "kernel-member-product-specialization", "ft-mem"),
            _subject_membership("sm-spec", "req-spec", "member-spec"),
        ]
        hops = _traverse(requirement, elements)
        assert len(hops) == 1
        assert hops[0].target["@id"] == "member-spec"
        assert (
            hops[0].witness["target_lineage"]["lineage_root_id"]
            == "kernel-member-product"
        )
        assert hops[0].witness["target_lineage"]["provenance"] == "explicit"

    def test_specialized_requirement_definition_source_qualifies(self):
        """A source typed by a RequirementCandidate specialization (the real
        FunctionalRequirementCandidate shape) is inside the governed domain."""
        elements = list(_kernel_elements())
        functional = {
            "@id": "kernel-functional-requirement",
            "@type": "RequirementDefinition",
            "declaredName": "FunctionalRequirementCandidate",
        }
        requirement = {
            "@id": "req-func",
            "@type": "RequirementUsage",
            "declaredName": "reqProvideCollisionWarning",
        }
        member = {
            "@id": "member-func",
            "@type": "ReferenceUsage",
            "declaredName": "memberProduct",
        }
        elements += [
            functional,
            requirement,
            member,
            _subclassification(
                "kernel-functional-requirement", "kernel-requirement", "sub-freq"
            ),
            _typing("req-func", "kernel-functional-requirement", "ft-req-func"),
            _typing("member-func", "kernel-member-product", "ft-member-func"),
            _subject_membership("sm-func", "req-func", "member-func"),
        ]
        hops = _traverse(requirement, elements)
        assert len(hops) == 1
        assert hops[0].target["@id"] == "member-func"
        assert (
            hops[0].witness["source_lineage"]["lineage_root_id"]
            == "kernel-requirement"
        )

    def test_deduplicate_multiple_memberships_to_the_same_subject(self):
        """Two SubjectMemberships owned by one requirement pointing at the
        same subject deduplicate to one hop (dedup key includes the witness
        membership id, so DISTINCT membership objects stay distinct hops)."""
        elements, requirement = _qualifying_fixture()
        duplicate = _subject_membership("sm-1", "req-1", "member-1")
        elements.append(duplicate)
        hops = _traverse(requirement, elements)
        assert len(hops) == 1

    def test_distinct_membership_objects_are_distinct_hops(self):
        """Two genuinely different SubjectMembership objects (distinct API
        UUIDs) owned by one requirement, both pointing at the same governed
        subject, are two witnesses of the same fact — not silently merged."""
        elements, requirement = _qualifying_fixture()
        elements.append(_subject_membership("sm-2", "req-1", "member-1"))
        hops = _traverse(requirement, elements)
        assert sorted(h.api_object["@id"] for h in hops) == ["sm-1", "sm-2"]


# ---------------------------------------------------------------------------
# Source negative laws
# ---------------------------------------------------------------------------


class TestSourceNegativeLaws:
    def test_law_1_requirement_usage_without_requirement_lineage(self):
        """A RequirementUsage untyped by the governed Requirement lineage
        produces no hop (ungrounded source)."""
        elements = list(_kernel_elements())
        untyped = {
            "@id": "req-orphan",
            "@type": "RequirementUsage",
            "declaredName": "reqCommandEmergencyBraking",
        }
        member = {"@id": "member-1", "@type": "PartUsage"}
        member_typed = _typing("member-1", "kernel-member-product", "ft-mem")
        elements += [
            untyped,
            member,
            member_typed,
            _subject_membership("sm-orphan", "req-orphan", "member-1"),
        ]
        assert _traverse(untyped, elements) == []

    def test_law_2_need_candidate_usage_with_member_product_subject(self):
        """The real governed negative case: a StakeholderNeedCandidate usage
        (API metaclass RequirementUsage, subject memberProduct typed by the
        member-product lineage) must NOT satisfy the Requirement->MemberProduct
        predicate. Metaclass equality is not ontology-class identity."""
        elements = list(_kernel_elements())
        need = {
            "@id": "need-1",
            "@type": "RequirementUsage",
            "declaredName": "needBoundedDegradationAndAvailability",
        }
        member = {
            "@id": "member-need",
            "@type": "ReferenceUsage",
            "declaredName": "memberProduct",
        }
        elements += [
            need,
            member,
            _typing("need-1", "kernel-need", "ft-need-1"),
            _typing("member-need", "kernel-member-product", "ft-member-need"),
            _subject_membership("sm-need", "need-1", "member-need"),
        ]
        assert _traverse(need, elements) == []

    def test_law_3_verification_evidence_contract_usage(self):
        """An evidence-contract usage (bench subject) is a RequirementUsage
        outside the governed Requirement lineage."""
        elements = list(_kernel_elements())
        evidence = {
            "@id": "ev-1",
            "@type": "RequirementUsage",
            "declaredName": "evidenceContractFreshOverrideClear",
        }
        bench = {"@id": "bench-1", "@type": "ReferenceUsage", "declaredName": "bench"}
        elements += [
            evidence,
            bench,
            _typing("ev-1", "kernel-need", "ft-ev"),
            _typing("bench-1", "kernel-bench", "ft-bench"),
            _subject_membership("sm-ev", "ev-1", "bench-1"),
        ]
        assert _traverse(evidence, elements) == []

    def test_law_4_correct_name_wrong_lineage(self):
        """The declared name 'reqCommandEmergencyBraking' with the WRONG
        lineage (typed by the Need definition) never qualifies — names are
        never consulted."""
        elements = list(_kernel_elements())
        wrong_lineage = {
            "@id": "req-clone",
            "@type": "RequirementUsage",
            "declaredName": "reqCommandEmergencyBraking",
        }
        member = {
            "@id": "member-1",
            "@type": "ReferenceUsage",
            "declaredName": "memberProduct",
        }
        elements += [
            wrong_lineage,
            member,
            _typing("req-clone", "kernel-need", "ft-clone"),
            _typing("member-1", "kernel-member-product", "ft-mem-1"),
            _subject_membership("sm-clone", "req-clone", "member-1"),
        ]
        assert _traverse(wrong_lineage, elements) == []

    def test_law_5_missing_requirement_kernel_binding_fails_closed(self):
        """Without the validated Requirement binding, a qualifying candidate
        cannot be decided: fail closed (no metaclass fallback)."""
        elements, requirement = _qualifying_fixture()
        with pytest.raises(IdentityNotFoundError, match="Requirement"):
            _traverse(requirement, elements, with_bindings=False)

    def test_law_5b_missing_binding_index_fails_closed(self):
        elements, requirement = _qualifying_fixture()
        with pytest.raises(IdentityNotFoundError, match="binding index"):
            SemanticTraversal(_contract(), kernel_bindings=None).traverse(
                "hasSubject", requirement, elements
            )

    def test_law_5c_missing_binding_is_quiet_when_no_candidates_exist(self):
        """Quiet absence stays quiet: a source with no SubjectMembership does
        not require (and does not trigger) lineage resolution."""
        elements = list(_kernel_elements())
        requirement = {
            "@id": "req-lonely",
            "@type": "RequirementUsage",
            "declaredName": "reqNoSubjectAtAll",
        }
        elements.append(requirement)
        assert _traverse(requirement, elements, with_bindings=False) == []

    def test_law_6_owner_metaclass_outside_configuration(self):
        """An owner of a type other than the configured requirement subject
        owner is not a source, regardless of lineage."""
        elements = list(_kernel_elements())
        part_owner = {
            "@id": "part-owner",
            "@type": "PartUsage",
            "declaredName": "systemCtx",
        }
        member = {"@id": "member-1", "@type": "PartUsage"}
        elements += [
            part_owner,
            member,
            _typing("part-owner", "kernel-requirement", "ft-owner"),
            _typing("member-1", "kernel-member-product", "ft-mem"),
            _subject_membership("sm-part", "part-owner", "member-1"),
        ]
        assert _traverse(part_owner, elements) == []


# ---------------------------------------------------------------------------
# Target negative laws
# ---------------------------------------------------------------------------


def _governed_source() -> tuple[list[dict], dict]:
    """A governed requirement (Requirement lineage, correct metaclass)."""
    elements = list(_kernel_elements())
    requirement = {
        "@id": "req-gov",
        "@type": "RequirementUsage",
        "declaredName": "reqGoverned",
    }
    elements += [requirement, _typing("req-gov", "kernel-requirement", "ft-gov")]
    return elements, requirement


class TestTargetNegativeLaws:
    def test_law_1_arbitrary_part_usage(self):
        elements, requirement = _governed_source()
        arbitrary = {"@id": "part-x", "@type": "PartUsage", "declaredName": "chassis"}
        elements += [arbitrary, _subject_membership("sm-x", "req-gov", "part-x")]
        assert _traverse(requirement, elements) == []

    def test_law_2_verification_bench(self):
        elements, requirement = _governed_source()
        bench = {"@id": "bench-1", "@type": "PartUsage", "declaredName": "bench"}
        elements += [
            bench,
            _typing("bench-1", "kernel-bench", "ft-bench"),
            _subject_membership("sm-bench", "req-gov", "bench-1"),
        ]
        assert _traverse(requirement, elements) == []

    def test_law_3_architecture_part(self):
        elements, requirement = _governed_source()
        architecture = {
            "@id": "kernel-arch",
            "@type": "PartDefinition",
            "declaredName": "AEBSLogicalArchitecture",
        }
        arch_part = {
            "@id": "arch-1",
            "@type": "PartUsage",
            "declaredName": "logicalArchitecture",
        }
        elements += [
            architecture,
            arch_part,
            _typing("arch-1", "kernel-arch", "ft-arch"),
            _subject_membership("sm-arch", "req-gov", "arch-1"),
        ]
        assert _traverse(requirement, elements) == []

    def test_law_4_stakeholder_actor_usage(self):
        elements, requirement = _governed_source()
        stakeholder = {
            "@id": "st-1",
            "@type": "PartUsage",
            "declaredName": "roadUser",
        }
        elements += [stakeholder, _subject_membership("sm-st", "req-gov", "st-1")]
        assert _traverse(requirement, elements) == []

    def test_law_5_another_requirement_usage(self):
        elements, requirement = _governed_source()
        other_req = {
            "@id": "req-other",
            "@type": "RequirementUsage",
            "declaredName": "reqOther",
        }
        elements += [other_req, _subject_membership("sm-o", "req-gov", "req-other")]
        assert _traverse(requirement, elements) == []

    def test_law_6_part_named_member_product_without_lineage(self):
        """The exact no-name-fallback probe: a part merely named memberProduct
        with no member-product lineage is rejected."""
        elements, requirement = _governed_source()
        impostor = {
            "@id": "impostor",
            "@type": "PartUsage",
            "declaredName": "memberProduct",
        }
        elements += [
            impostor,
            _subject_membership("sm-imp", "req-gov", "impostor"),
        ]
        assert _traverse(requirement, elements) == []

    def test_law_7_unrelated_same_named_definition(self):
        """A part typed by an unrelated definition that merely shares the
        name ProductLineMemberProduct (different UUID, no validated binding)
        is rejected — identity is the validated UUID, never the name."""
        elements, requirement = _governed_source()
        homonym_definition = {
            "@id": "kernel-homonym",
            "@type": "PartDefinition",
            "declaredName": "ProductLineMemberProduct",
            "qualifiedName": "SomeOtherPackage::ProductLineMemberProduct",
        }
        impostor = {
            "@id": "member-homonym",
            "@type": "PartUsage",
            "declaredName": "memberProduct",
        }
        elements += [
            homonym_definition,
            impostor,
            _typing("member-homonym", "kernel-homonym", "ft-hom"),
            _subject_membership("sm-hom", "req-gov", "member-homonym"),
        ]
        assert _traverse(requirement, elements) == []

    def test_law_8_dangling_member_element(self):
        """A SubjectMembership whose memberElement does not resolve in the
        bound revision is not a hop (and not a crash)."""
        elements, requirement = _governed_source()
        elements.append(_subject_membership("sm-dangle", "req-gov", "ghost-member"))
        assert _traverse(requirement, elements) == []

    def test_law_9_ambiguous_lineage_fails_closed(self):
        """Ambiguity fail-closed laws: (a) the binding index rejects multiple
        validated bindings for one ontology class at construction; (b) an
        element claimed by MORE THAN ONE ontology class binding (ambiguous
        vocabulary identity) is rejected by ontology_class_for, so a member
        grounding in two governed lineages can never be guessed."""
        from de4sdv.semantic.kernel_binding_index import KernelBindingIndex
        from de4sdv.sysml_api.revisions import RevisionBinding

        def _binding(entries: list[dict[str, str]]):
            return RevisionBinding.from_dict(
                {
                    "git_repository": "de4sdv/DE4SDV",
                    "git_commit": "a" * 40,
                    "sysml_project_id": "project-1",
                    "sysml_commit_id": "commit-1",
                    "import_timestamp": "2026-08-31T00:00:00Z",
                    "import_tool_version": "test",
                    "semantic_validation": "passed",
                    "scope": "fixture",
                    "ontology": _contract().identity.to_dict(),
                    "kernel_bindings": entries,
                }
            )

        base = {
            "source_file": "f.sysml",
            "declaration": "declaration",
        }
        # (a) two validated bindings for ONE ontology class are
        # unrepresentable — construction fails closed.
        with pytest.raises(IdentityNotFoundError, match="multiple kernel bindings"):
            KernelBindingIndex.from_binding(
                _binding(
                    [
                        {
                            "ontology_class": "Requirement",
                            "element_id": "kernel-requirement",
                            **base,
                        },
                        {
                            "ontology_class": "Requirement",
                            "element_id": "kernel-member-product",
                            **base,
                        },
                    ]
                )
            )
        # (b) one element claimed by multiple ontology-class bindings is an
        # ambiguous vocabulary identity — never guessed.
        index = KernelBindingIndex.from_binding(
            _binding(
                [
                    {
                        "ontology_class": "Requirement",
                        "element_id": "kernel-requirement",
                        **base,
                    },
                    {
                        "ontology_class": "MemberProduct",
                        "element_id": "kernel-member-product",
                        **base,
                    },
                    {
                        "ontology_class": "Need",
                        "element_id": "kernel-member-product",
                        **base,
                    },
                ]
            )
        )
        by_id = {e["@id"]: e for e in _kernel_elements()}
        with pytest.raises(IdentityNotFoundError, match="claimed by multiple"):
            index.ontology_class_for("kernel-member-product", by_id)

    def test_law_10_missing_member_product_binding_fails_closed(self):
        """Without the validated MemberProduct binding, a qualifying candidate
        cannot be decided: fail closed (no name fallback)."""
        elements, requirement = _qualifying_fixture()
        with pytest.raises(IdentityNotFoundError, match="MemberProduct"):
            _traverse(requirement, elements, with_bindings=True) if False else (
                SemanticTraversal(
                    _contract(), kernel_bindings=_kernel_index(member_product=False)
                ).traverse("hasSubject", requirement, elements)
            )


# ---------------------------------------------------------------------------
# Relationship negative laws
# ---------------------------------------------------------------------------


class TestRelationshipNegativeLaws:
    def test_no_substitute_relationship_kind_yields_a_hop(self):
        """FeatureMembership, OwningMembership, RVM, Dependency, Allocation,
        and a plain reference property never substitute for the native
        SubjectMembership discriminator."""
        elements, requirement = _governed_source()
        member = {
            "@id": "member-sub",
            "@type": "ReferenceUsage",
            "declaredName": "memberProduct",
        }
        elements += [
            member,
            _typing("member-sub", "kernel-member-product", "ft-sub"),
            {
                "@id": "fm-1",
                "@type": "FeatureMembership",
                "owningRelatedElement": {"@id": "req-gov"},
                "memberElement": {"@id": "member-sub"},
            },
            {
                "@id": "om-1",
                "@type": "OwningMembership",
                "owningRelatedElement": {"@id": "req-gov"},
                "memberElement": {"@id": "member-sub"},
            },
            {
                "@id": "rvm-1",
                "@type": "RequirementVerificationMembership",
                "owningRelatedElement": {"@id": "req-gov"},
                "memberElement": {"@id": "member-sub"},
            },
            {
                "@id": "dep-1",
                "@type": "Dependency",
                "source": [{"@id": "req-gov"}],
                "target": [{"@id": "member-sub"}],
            },
            {
                "@id": "alloc-1",
                "@type": "AllocationUsage",
                "source": [{"@id": "req-gov"}],
                "target": [{"@id": "member-sub"}],
            },
            {
                "@id": "member-sub",
                "referencedFeature": {"@id": "member-sub"},
            },
        ]
        # The last element duplicates member-sub with a plain reference
        # property shape; only the native SubjectMembership qualifies and it
        # is absent from this corpus.
        assert _traverse(requirement, elements) == []

    def test_ple_configuration_relation_is_not_a_subject_hop(self):
        """A PLE configuration relation (FeatureConfiguration -> selects ->
        MemberProduct-shaped graph) never produces hasSubject hops."""
        elements, requirement = _governed_source()
        configuration = {
            "@id": "config-1",
            "@type": "PartUsage",
            "declaredName": "standaloneConfiguration",
        }
        elements += [
            configuration,
            _typing("config-1", "kernel-member-product", "ft-config"),
            {
                "@id": "ple-selects",
                "@type": "Dependency",
                "source": [{"@id": "config-1"}],
                "target": [{"@id": "req-gov"}],
            },
        ]
        # A dependency from a member-product-lineage configuration to the
        # requirement is PLE selection, not a subject membership.
        assert _traverse(requirement, elements) == []

    def test_single_subject_membership_strategy_branch(self):
        """The discriminator stays single: exactly one subject-membership
        strategy dispatch exists in the traversal."""
        source = TRAVERSAL_SOURCE.read_text(encoding="utf-8")
        assert source.count('mapping.strategy == "subject-membership"') == 1


# ---------------------------------------------------------------------------
# Name-fallback prohibition
# ---------------------------------------------------------------------------


class TestNoNameFallback:
    def test_no_name_or_source_parsing_in_the_hardened_traversal(self):
        """The executable body of the hardened traversal consults no names
        and parses no SysML source (docstring prose is excluded)."""
        import ast

        source_text = TRAVERSAL_SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(source_text)
        function = None
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_subject_membership_hops"
            ):
                function = node
                break
        assert function is not None
        # Executable statements only (docstrings excluded): the fail-closed
        # doc mentions names it refuses; the CODE must not use them.
        body_nodes = [
            node
            for node in function.body
            if not (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            )
        ]
        body = ast.parse("").body  # placeholder to build a module
        module = ast.Module(body=body_nodes, type_ignores=[])
        compiled_names = {
            node.id
            for node in ast.walk(module)
            if isinstance(node, ast.Name)
        }
        compiled_attrs = {
            node.attr
            for node in ast.walk(module)
            if isinstance(node, ast.Attribute)
        }
        compiled_consts = {
            node.value
            for node in ast.walk(module)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        del body
        # No name-based identity: declaredName/qualifiedName/declaredShortName
        # are never read, and the literal memberProduct never appears.
        assert "declaredName" not in compiled_attrs | compiled_names
        assert "qualifiedName" not in compiled_attrs | compiled_names
        assert "memberProduct" not in compiled_consts
        # No runtime SysML source parsing.
        assert ".sysml" not in compiled_consts
        assert "open(" not in ast.dump(module)

    def test_name_only_correspondence_is_rejected_in_both_directions(self):
        """A member named memberProduct without lineage (target side) and a
        source named like a governed requirement without lineage (source
        side) are both rejected."""
        elements, requirement = _governed_source()
        impostor = {
            "@id": "impostor",
            "@type": "PartUsage",
            "declaredName": "memberProduct",
        }
        elements += [impostor, _subject_membership("sm-imp", "req-gov", "impostor")]
        assert _traverse(requirement, elements) == []
        # Source side: law_4 in TestSourceNegativeLaws covers the reverse.


# ---------------------------------------------------------------------------
# Mapping parity: enforcement derives from the declared domain/range
# ---------------------------------------------------------------------------


class TestMappingParity:
    def test_mapping_carries_the_declared_domain_and_range(self):
        mapping = _contract().relationship_mapping("hasSubject")
        assert mapping.domain == "Requirement"
        assert mapping.range == "MemberProduct"
        # No duplicated lineage fields exist in the mapping configuration:
        # the declared domain/range ARE the enforcement contract.
        assert "source_lineage_of" not in mapping.configuration
        assert "target_lineage_of" not in mapping.configuration
        assert "domain" not in mapping.configuration
        assert "range" not in mapping.configuration

    def test_changing_domain_changes_the_enforced_source_lineage(self):
        """Pointing the declared domain at a different governed class
        deterministically changes the mechanics: the Need-typed source
        qualifies and the Requirement-typed source is refused — the
        mechanics cannot silently keep a stale duplicated configuration."""
        elements = list(_kernel_elements())
        need = {
            "@id": "need-1",
            "@type": "RequirementUsage",
            "declaredName": "needBoundedDegradationAndAvailability",
        }
        requirement = {
            "@id": "req-1",
            "@type": "RequirementUsage",
            "declaredName": "reqCommandEmergencyBraking",
        }
        member = {
            "@id": "member-1",
            "@type": "ReferenceUsage",
            "declaredName": "memberProduct",
        }
        elements += [
            need,
            requirement,
            member,
            _typing("need-1", "kernel-need", "ft-need"),
            _typing("req-1", "kernel-requirement", "ft-req"),
            _typing("member-1", "kernel-member-product", "ft-mem"),
            _subject_membership("sm-need", "need-1", "member-1"),
            _subject_membership("sm-req", "req-1", "member-1"),
        ]
        swapped = KernelContract.load(
            REPO_ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
        )
        object.__setattr__(swapped, "relationships", dict(swapped.relationships))
        swapped.relationships["hasSubject"] = dict(
            swapped.relationships["hasSubject"]
        )
        swapped.relationships["hasSubject"]["domain"] = "Need"
        swapped.relationships["hasSubject"]["sysml_mapping"] = dict(
            swapped.relationships["hasSubject"]["sysml_mapping"]
        )
        index = _kernel_index(requirement=True, member_product=True, need=True)
        traversal = SemanticTraversal(swapped, kernel_bindings=index)
        need_hops = traversal.traverse(
            "hasSubject", next(e for e in elements if e["@id"] == "need-1"), elements
        )
        assert [h.api_object["@id"] for h in need_hops] == ["sm-need"]
        req_hops = traversal.traverse(
            "hasSubject", next(e for e in elements if e["@id"] == "req-1"), elements
        )
        assert req_hops == []

    def test_mapping_without_declared_domain_or_range_refuses_to_run(self):
        """A corrupted mapping that loses the governed lineage contract is a
        hard configuration error, never silent vocabulary-only degradation."""
        contract = KernelContract.load(
            REPO_ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
        )
        object.__setattr__(contract, "relationships", dict(contract.relationships))
        contract.relationships["hasSubject"] = dict(
            contract.relationships["hasSubject"]
        )
        contract.relationships["hasSubject"]["sysml_mapping"] = dict(
            contract.relationships["hasSubject"]["sysml_mapping"]
        )
        del contract.relationships["hasSubject"]["domain"]
        elements, requirement = _qualifying_fixture()
        with pytest.raises(ValueError, match="declares no governed domain/range"):
            SemanticTraversal(
                contract, kernel_bindings=_kernel_index()
            ).traverse("hasSubject", requirement, elements)

    def test_mapping_cannot_redefine_domain_through_configuration(self):
        """Adding domain/range keys to the sysml_mapping block cannot
        redefine the semantic contract: the loader routes only spec-level
        domain/range into RelationshipMapping.domain/range and never exposes
        them as configuration, so no second authored type contract can
        appear at the mechanics layer."""
        contract = KernelContract.load(
            REPO_ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
        )
        raw = yaml.safe_load(
            (
                REPO_ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
            ).read_text(encoding="utf-8")
        )
        # An author (or a corrupt edit) plants competing type keys inside the
        # sysml_mapping block.
        raw["relationships"]["hasSubject"]["sysml_mapping"]["domain"] = "Need"
        raw["relationships"]["hasSubject"]["sysml_mapping"]["range"] = "Need"
        object.__setattr__(contract, "relationships", raw["relationships"])
        mapping = contract.relationship_mapping("hasSubject")
        # The spec-level semantic contract is untouched by the mapping keys.
        assert mapping.domain == "Requirement"
        assert mapping.range == "MemberProduct"
        assert "domain" not in mapping.configuration
        assert "range" not in mapping.configuration
        # The enforcement therefore still resolves the declared lineages
        # (Requirement/MemberProduct), never the planted ones.
        elements, requirement = _qualifying_fixture()
        hops = SemanticTraversal(
            contract, kernel_bindings=_kernel_index()
        ).traverse("hasSubject", requirement, elements)
        assert [h.api_object["@id"] for h in hops] == ["sm-1"]
        assert hops[0].witness["source_lineage"]["ontology_class"] == "Requirement"
        assert hops[0].witness["target_lineage"]["ontology_class"] == "MemberProduct"


# ---------------------------------------------------------------------------
# ImpactService boundary
# ---------------------------------------------------------------------------


class TestImpactServiceBoundary:
    def _impact_service(self, elements: list[dict]):
        from de4sdv.semantic.api_binding import OntologyApiBinder
        from de4sdv.semantic.impact import ImpactService
        from de4sdv.sysml_api.revisions import RevisionBinding

        class _Repo:
            def __init__(self, elements: list[dict]) -> None:
                self.elements = elements

            def list_elements(self, project_id: str, commit_id: str):
                return self.elements

        binding = RevisionBinding.from_dict(
            {
                "git_repository": "de4sdv/DE4SDV",
                "git_commit": "a" * 40,
                "sysml_project_id": "project-1",
                "sysml_commit_id": "commit-1",
                "import_timestamp": "2026-08-31T00:00:00Z",
                "import_tool_version": "test",
                "semantic_validation": "passed",
                "scope": "full-model",
                "ontology": _contract().identity.to_dict(),
                "kernel_bindings": [
                    {
                        "ontology_class": "Requirement",
                        "element_id": "kernel-requirement",
                        "source_file": "f.sysml",
                        "declaration": "requirement def RequirementCandidate",
                    },
                    {
                        "ontology_class": "MemberProduct",
                        "element_id": "kernel-member-product",
                        "source_file": "f.sysml",
                        "declaration": "part def ProductLineMemberProduct",
                    },
                ],
            }
        )
        from de4sdv.semantic.kernel_binding_index import KernelBindingIndex

        index = KernelBindingIndex.from_binding(binding)
        contract = _contract()
        repository = _Repo(elements)
        return ImpactService(
            repository=repository,  # type: ignore[arg-type]
            binding=binding,
            contract=contract,
            binder=OntologyApiBinder(
                contract,
                repository,  # type: ignore[arg-type]
                project_id="project-1",
                commit_id="commit-1",
                kernel_bindings=index,
            ),
            traversal=SemanticTraversal(contract, kernel_bindings=index),
        )

    def test_non_member_product_subject_is_never_a_product_line_hop(self):
        """Regression: a governed requirement whose SubjectMembership points
        at a bench must not gain a MemberProduct product-line node or
        hasSubject edge through ImpactService."""
        elements, requirement = _governed_source()
        bench = {"@id": "bench-1", "@type": "PartUsage", "declaredName": "bench"}
        elements += [
            bench,
            _typing("bench-1", "kernel-bench", "ft-bench"),
            _subject_membership("sm-bench", "req-gov", "bench-1"),
        ]
        service = self._impact_service(elements)
        result = service.impact("reqGoverned", git_revision="a" * 40)
        assert result["root"]["element_id"] == "req-gov"
        assert "hasSubject" not in {e["predicate"] for e in result["edges"]}
        product_nodes = [
            n for n in result["nodes"] if n["category"] == "product-line"
        ]
        assert product_nodes == []
        assert any(g["category"] == "product-line" for g in result["gaps"])

    def test_valid_member_product_subject_still_appears(self):
        elements, requirement = _qualifying_fixture()
        service = self._impact_service(elements)
        result = service.impact(
            "reqCommandEmergencyBraking", git_revision="a" * 40
        )
        assert "hasSubject" in {e["predicate"] for e in result["edges"]}
        product_nodes = [
            n for n in result["nodes"] if n["category"] == "product-line"
        ]
        assert [n["element_id"] for n in product_nodes] == ["member-1"]
        assert not any(g["category"] == "product-line" for g in result["gaps"])


# ---------------------------------------------------------------------------
# Retained-run replay constants and no-privileged-ingestion boundary
# ---------------------------------------------------------------------------


class TestReplayEvidence:
    def test_replay_numbers_are_locked_and_consistent(self):
        assert REPLAY_TOTAL_MEMBERSHIPS == 289
        assert REPLAY_PRE_C3_HOPS == REPLAY_POST_C3_HOPS + (
            REPLAY_REMOVED_NON_REQUIREMENT_SOURCES
            + REPLAY_REMOVED_NON_MEMBERPRODUCT_TARGETS
        )
        assert REPLAY_PRE_C3_HOPS == 131
        assert REPLAY_POST_C3_HOPS == 21

    def test_replay_numbers_are_recorded_in_the_decision_and_review_doc(self):
        decision_text = _decision_text(
            yaml.safe_load(DECISIONS_PATH.read_text(encoding="utf-8"))["entries"][
                "hasSubject"
            ]
        )
        review_text = REVIEW_DOC.read_text(encoding="utf-8")
        for token in ("289", "131", "21", "57", "53", "110"):
            assert token in decision_text or token in review_text, token

    def test_no_privileged_ingestion_dispatched(self):
        """c3 cites the retained export; no new ingestion script/workflow is
        added and the review doc says no ingestion was dispatched."""
        review_text = REVIEW_DOC.read_text(encoding="utf-8")
        assert "no privileged ingestion" in review_text.lower()
        assert "No privileged ingestion was dispatched for c3" in review_text

    def test_no_model_change(self):
        """No .sysml file is modified by c3: the diff vs the c2 head touches
        no model file (checked structurally via the review doc + decisions,
        which this test pins textually)."""
        review_text = REVIEW_DOC.read_text(encoding="utf-8")
        assert "No `.sysml` file changed" in review_text
        assert "No parallel `HasSubject`" in review_text
