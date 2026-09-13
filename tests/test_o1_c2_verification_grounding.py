"""O1 c2 — verification native/library semantic grounding (PR #249).

Covers the c2 claim for exactly two identities:

- class ``VerificationCase`` — the native SysML verification-case construct,
  grounded (for the real DE4SDV constructs) through the toolchain-materialized
  standard-library relationships to ``VerificationCases::VerificationCase``
  (definition) and ``VerificationCases::verificationCases`` (usage);
- relationship ``verifiedBy`` — native verification-objective semantics:
  ``Requirement -> VerificationCase`` as reverse navigation over the native
  ``RequirementVerificationMembership`` / objective-ownership witness.

The batch tests:

1.  exactly ``VerificationCase`` + ``verifiedBy`` comprise c2 (no third
    identity promoted; the global parity set is the seven c1 rows plus these
    two);
2.  authority is unchanged: ``VerificationCase`` stays ``native-sysml``,
    ``verifiedBy`` stays ``legacy-yaml`` (no O3 cutover); targets stay
    ``native-sysml``;
3.  both rows are ``parity-reviewed`` — retained Lane B exact-toolchain
    evidence is supporting evidence only, not revision-bound to this
    inventory revision (no ``exact-toolchain-validated`` /
    ``privileged-closure-proven`` claim, no closure record, no supported
    promotion);
4.  the reviewed decisions record the exact-fit results, the definition/usage
    anchor distinction, explicit-vs-implied grounding provenance, and the
    bounded claim (declared verification objective only);
5.  the reviewed c2 decision fields carry no stronger claims (no execution
    outcome, no acceptance, no validation/certification);
6.  the standard-grounding proof contract is machine-locked from the real
    machinery: read-back per-usage/definition grounding witnesses (metaclass
    kept DISTINCT from library grounding — UG-28) and the
    RequirementVerificationMembership objective-chain resolution through the
    live traversal;
7.  the negative semantic laws: metaclass-alone, missing authored
    definition/usage relationship, wrong library anchor, wrong library
    document, name-only correspondence, generic Dependency, SubjectMembership,
    VerificationMethod metadata, retained-evidence presence, and
    outcome/PASS-like metadata are all NOT sufficient;
8.  the traversal stays fail-closed and single: exactly one
    verification-membership strategy branch with the reviewed configuration;
9.  no runtime/query/model semantics changed and no new Semantic Projection
    row appears; c1/c3–c5/PLE/K states are unchanged.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic import authority_inventory as ai
from de4sdv.semantic.traversal import SemanticTraversal

from test_lane_b_v11_round import (  # noqa: E402 - shared real-shape fixtures
    LIBRARY_DEFINITION_ANCHOR,
    LIBRARY_USAGE_SET_ANCHOR,
    _full_pilot_import,
    _run_readback,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

INVENTORY_PATH = (
    REPO_ROOT / "docs/method-conformance/o1/semantic-authority-inventory.json"
)
DECISIONS_PATH = (
    REPO_ROOT / "docs/method-conformance/o1/authority-review-decisions.yaml"
)
CLOSURE_PATH = REPO_ROOT / "docs/method-conformance/o1/closure-evidence.json"
PILOT_MODEL = (
    REPO_ROOT
    / "textual-notation-of-model/packages/features/aebs/aebs_override_verification.sysml"
)

#: The c2 batch is exactly these two identities — no third entry.
C2_IDENTITIES: tuple[str, ...] = ("VerificationCase", "verifiedBy")

#: The seven c1 identities accepted as parity-reviewed (unchanged by c2).
C1_ACCEPTED: tuple[str, ...] = (
    "MethodPhase",
    "MethodContractObligation",
    "EvaluationSourceKind",
    "EvaluationScopeMembership",
    "TestedScopeDeclaration",
    "RetainedExecutionRecordReference",
    "AcceptanceAttestationReference",
)

#: The one c1 identity that stays incomplete (no c2 silent closure).
C1_INCOMPLETE: tuple[str, ...] = ("MethodEvaluationScope",)

#: PLE-family rows under the adoption gate (unchanged by c2).
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

#: K rows with the r6-3 closure record (unchanged by c2).
K_TRIPLE: tuple[str, ...] = (
    "DerivesFromNeed",
    "derivesRequirementFromNeed",
    "derivedRequirementsOfNeed",
)

#: Synthetic serializer fixtures (synthetic ids, real machinery).
DEFINITION_ELEMENT_ID = "00000000-0000-4000-8000-0000000000d0"
DEFINITION_GROUNDING_EDGE_ID = "99999999-0000-4000-8000-0000000000d1"
USAGE_01_TYPING_EDGE_ID = "00000000-0000-4000-8000-0000000000g1"
USAGE_01_SUBSETTING_EDGE_ID = "00000000-0000-4000-8000-00000000ss01"

#: Outcome/evidence vocabulary that must never appear as a c2 claim.
_FORBIDDEN_CLAIM_PATTERNS = (
    (re.compile(r"\bexecuted successfully\b", re.IGNORECASE), "executed successfully"),
    (re.compile(r"\bPASS\b"), "PASS"),
    (re.compile(r"\baccepted\b", re.IGNORECASE), "accepted"),
    (re.compile(r"\bevidence complete\b", re.IGNORECASE), "evidence complete"),
    (re.compile(r"\bsatisfied by\b", re.IGNORECASE), "satisfied by"),
    (re.compile(r"\bvalidated\b", re.IGNORECASE), "validated"),
    (re.compile(r"\bcertified\b", re.IGNORECASE), "certified"),
)


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


def _contract() -> ai.KernelContract:
    return ai.KernelContract.load(REPO_ROOT / ai.ONTOLOGY_PATH)


def _traverse(requirement: dict, elements: list[dict]):
    return SemanticTraversal(_contract()).traverse("verifiedBy", requirement, elements)


def _requirement(req_id: str, name: str = "evidenceContractSample") -> dict:
    return {"@id": req_id, "@type": "RequirementUsage", "declaredName": name}


def _verification_case(
    case_id: str, kind: str = "VerificationCaseUsage"
) -> dict:
    return {"@id": case_id, "@type": kind, "declaredName": "sampleVerification"}


def _rvm(rvm_id: str, owner_id: str, member_id: str) -> dict:
    return {
        "@id": rvm_id,
        "@type": "RequirementVerificationMembership",
        "owningRelatedElement": {"@id": owner_id},
        "memberElement": {"@id": member_id},
    }


def _objective_chain_elements(*, case_kind: str = "VerificationCaseDefinition"):
    """The real imported shape: requirement <- RVM <- objective <- case."""
    return [
        _requirement("req-1"),
        _verification_case("vc-def-1", case_kind),
        {
            "@id": "objective-1",
            "@type": "RequirementUsage",
            "declaredName": "evidenceObjective",
        },
        {
            "@id": "om-1",
            "@type": "ObjectiveMembership",
            "owningRelatedElement": {"@id": "vc-def-1"},
            "memberElement": {"@id": "objective-1"},
        },
        _rvm("rvm-1", "objective-1", "req-1"),
    ]


def _decision_text(row: dict) -> str:
    """The bounded reviewed-decision fields of one c2 row."""
    parts = [str(row.get("note") or ""), str(row.get("exact_fit_decision") or "")]
    parts.extend(str(item) for item in row.get("required_evidence") or [])
    parts.extend(str(item) for item in row.get("unknowns") or [])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# c2 scope and inventory state
# ---------------------------------------------------------------------------


class TestC2ScopeAndCounts:
    def test_c2_is_exactly_two_identities(self):
        assert len(C2_IDENTITIES) == 2
        assert len(set(C2_IDENTITIES)) == 2

    def test_both_identities_are_ontology_entries(self, inventory, decisions):
        entries = _entries(inventory)
        assert set(C2_IDENTITIES) <= set(entries)
        assert entries["VerificationCase"]["kind"] == "class"
        assert entries["verifiedBy"]["kind"] == "relationship"
        assert set(C2_IDENTITIES) <= set(decisions["entries"])

    def test_only_c2_identities_carry_the_c2_stage(self, inventory):
        """Exactly the two c2 rows are staged to the verification batch: no
        third identity was moved into c2."""
        staged = [
            entry["identity"]
            for entry in inventory["entries"]
            if str(entry["reviewed"]["stage"]).startswith("c2")
        ]
        assert sorted(staged) == sorted(C2_IDENTITIES)

    def test_global_parity_set_is_c1_plus_c2(self, inventory):
        """No third identity is promoted: the parity-reviewed set is exactly
        the seven c1 rows plus the two c2 rows."""
        parity = {
            entry["identity"]
            for entry in inventory["entries"]
            if entry["reviewed"]["evidence_state"] == "parity-reviewed"
        }
        assert parity == set(C1_ACCEPTED) | set(C2_IDENTITIES)
        assert len(parity) == 9

    def test_authority_current_unchanged(self, inventory):
        entries = _entries(inventory)
        assert (
            entries["VerificationCase"]["reviewed"]["authority_current"]
            == "native-sysml"
        )
        assert entries["verifiedBy"]["reviewed"]["authority_current"] == "legacy-yaml"

    def test_authority_targets_remain_native_sysml(self, inventory):
        for entry in _entries(inventory, C2_IDENTITIES).values():
            assert entry["reviewed"]["authority_target"] == "native-sysml"

    def test_evidence_states_are_parity_reviewed(self, inventory):
        for entry in _entries(inventory, C2_IDENTITIES).values():
            assert entry["reviewed"]["evidence_state"] == "parity-reviewed"

    def test_no_closure_evidence_and_no_privileged_claim(self, inventory):
        for entry in _entries(inventory, C2_IDENTITIES).values():
            assert entry["reviewed"]["closure_evidence_ref"] is None
            assert entry["reviewed"]["evidence_state"] != "privileged-closure-proven"
        # The retained closure dataset still carries only the K record.
        closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
        assert len(closure["records"]) == 1
        assert closure["records"][0]["id"] == "r6-3"
        for name in C2_IDENTITIES:
            assert name not in closure["records"][0]["subject_identities"]

    def test_no_supported_promotion(self, inventory):
        entries = _entries(inventory, C2_IDENTITIES)
        for entry in entries.values():
            assert entry["reviewed"]["adoption_status"] == "not-applicable"
            consumption = entry["reviewed"].get("runtime_consumption") or {}
            assert consumption.get("support") != "supported (closure-verified)"
        # The reviewed consumer provenance of VerificationCase is unchanged.
        consumption = entries["VerificationCase"]["reviewed"]["runtime_consumption"]
        assert consumption["support"] == "consumed (verifiedBy)"
        # The verifiedBy runtime support is unchanged (still the legacy-yaml
        # mapping driving the native-verification traversal).
        assert (
            entries["verifiedBy"]["observed"]["runtime_support"]
            == "implemented (verification-membership)"
        )

    def test_no_c2_row_is_conditional(self, inventory):
        for entry in _entries(inventory, C2_IDENTITIES).values():
            assert entry["reviewed"]["conditional_target"] is False
            assert entry["reviewed"]["transition_gate"] is None

    def test_no_new_semantic_projection_row(self):
        """The Semantic Projection consumer de4sdv/semantic/projection.py is
        bound to the K-slice classes only; c2 rows are governance rows in the
        inventory, not generated projection rows."""
        source = (REPO_ROOT / "de4sdv/semantic/projection.py").read_text(
            encoding="utf-8"
        )
        for name in C2_IDENTITIES:
            assert f'"{name}"' not in source, name

    def test_expected_evidence_state_counts(self, inventory):
        """c2 changes evidence maturity only: parity 7 -> 9, evidence 68 -> 66;
        every other evidence class is unchanged."""
        assert inventory["evidence_state_counts"] == {
            "blocked": 14,
            "parity-reviewed": 9,
            "privileged-closure-proven": 3,
            "repository-evidenced": 66,
            "unknown": 1,
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

    def test_c1_rows_unchanged(self, inventory):
        entries = _entries(inventory)
        for name in C1_ACCEPTED:
            row = entries[name]["reviewed"]
            assert row["authority_current"] == "legacy-yaml", name
            assert row["authority_target"] == "model-authoritative", name
            assert row["evidence_state"] == "parity-reviewed", name
            assert row["closure_evidence_ref"] is None, name
        for name in C1_INCOMPLETE:
            row = entries[name]["reviewed"]
            assert row["authority_current"] == "legacy-yaml", name
            assert row["evidence_state"] == "repository-evidenced", name

    def test_c3_to_c5_rows_unchanged(self, inventory):
        entries = _entries(inventory)
        expected = {
            "hasSubject": ("c3", "legacy-yaml", "repository-evidenced"),
            "derivesNeedFromConcern": ("c4", "legacy-yaml", "blocked"),
            "realizedBy": ("c5", "legacy-yaml", "repository-evidenced"),
            "specifiesFunction": ("c5", "legacy-yaml", "repository-evidenced"),
            "hasRelevantArchitecture": ("c5", "legacy-yaml", "repository-evidenced"),
            "hasRelevantEvidenceContract": ("c5", "legacy-yaml", "repository-evidenced"),
        }
        for identity, (stage, authority, evidence) in expected.items():
            row = entries[identity]["reviewed"]
            assert row["stage"] == stage, identity
            assert row["authority_current"] == authority, identity
            assert row["evidence_state"] == evidence, identity

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


# ---------------------------------------------------------------------------
# Reviewed decision record content and claim boundary
# ---------------------------------------------------------------------------


class TestC2DecisionRecord:
    def _row(self, decisions: dict, name: str) -> dict:
        return decisions["entries"][name]

    def test_verificationcase_records_definition_and_usage_anchors(self, decisions):
        row = self._row(decisions, "VerificationCase")
        text = _decision_text(row)
        assert "VerificationCases::VerificationCase" in text
        assert "VerificationCases::verificationCases" in text
        # The definition/usage distinction is explicit.
        assert "definition" in text and "usage" in text

    def test_verificationcase_records_metaclass_vs_grounding_separation(self, decisions):
        row = self._row(decisions, "VerificationCase")
        text = _decision_text(row)
        assert "separate evidence field from the library grounding" in text
        assert "UG-28" in text
        assert "metaclass alone is not the semantic proof" in text

    def test_verificationcase_records_grounding_provenance(self, decisions):
        row = self._row(decisions, "VerificationCase")
        text = _decision_text(row)
        assert "toolchain-implied" in text
        assert "explicitly authored" in text
        assert "implied" in text

    def test_verificationcase_records_retained_evidence_reference(self, decisions):
        """The retained Lane B evidence is cited as supporting evidence only,
        not as a revision-bound carry-forward claim."""
        row = self._row(decisions, "VerificationCase")
        text = _decision_text(row)
        assert "34576049742" in text
        assert "0a23902370de9fc74d6118afe480382e0b0d8aa0" in text
        assert "supporting evidence only" in text

    def test_verificationcase_exact_fit_decision(self, decisions):
        row = self._row(decisions, "VerificationCase")
        decision = row["exact_fit_decision"]
        assert decision.startswith("exact fit:")
        assert "native construct" in decision
        assert "no parallel application class" in decision

    def test_verifiedby_records_native_identity_and_query(self, decisions):
        row = self._row(decisions, "verifiedBy")
        text = _decision_text(row)
        assert "RequirementVerificationMembership" in text
        assert "Requirement -> VerificationCase" in text
        assert "reverse navigation" in text

    def test_verifiedby_records_mechanics_boundary(self, decisions):
        row = self._row(decisions, "verifiedBy")
        note = row["note"]
        assert "sysml_mapping" in note
        assert "not themselves the engineering meaning" in note
        # Mechanics recorded as such: owner chain, reference property, direction.
        assert "owner-chain" in note
        assert "reference property" in note

    def test_verifiedby_records_claim_boundary(self, decisions):
        row = self._row(decisions, "verifiedBy")
        note = row["note"]
        assert "declared as a verification objective" in note
        assert "declared verification-objective / coverage relation only" in note
        assert "no execution, outcome, satisfaction" in note
        # Authority boundary: legacy-yaml stays the O1 authority.
        assert "remains current authority during O1" in note

    def test_verifiedby_exact_fit_decision_names_the_laws(self, decisions):
        row = self._row(decisions, "verifiedBy")
        decision = row["exact_fit_decision"]
        assert decision.startswith("exact fit:")
        for fragment in (
            "RequirementVerificationMembership",
            "generic Dependency",
            "SubjectMembership",
            "VerificationMethod",
            "name-only correspondence",
            "no name-based fallback",
        ):
            assert fragment in decision, fragment

    def test_claim_boundary_fields_free_of_outcome_claims(self, decisions):
        """Pin the bounded reviewed c2 decision fields: no stronger claim
        (execution outcome, PASS-like verdict, acceptance,
        evidence-completeness, satisfaction-by-product, validation,
        certification) appears in either c2 decision record."""
        for name in C2_IDENTITIES:
            text = _decision_text(self._row(decisions, name))
            for pattern, label in _FORBIDDEN_CLAIM_PATTERNS:
                assert pattern.search(text) is None, (name, label)

    def test_required_evidence_is_a_forward_path(self, decisions):
        for name in C2_IDENTITIES:
            row = self._row(decisions, name)
            assert row["required_evidence"], name
            joined = " ".join(row["required_evidence"])
            assert "O2" in joined, name
            assert "closure" not in joined.lower(), name


# ---------------------------------------------------------------------------
# Standard-grounding proof contract (real machinery, synthetic fixtures)
# ---------------------------------------------------------------------------


class TestStandardGroundingContract:
    def test_definition_grounding_shape(self, tmp_path, monkeypatch):
        """VerificationCaseDefinition + implied Subclassification witness to
        the VerificationCases::VerificationCase anchor; API metaclass and
        library grounding are separate fields (UG-28)."""
        out, _ = _run_readback(monkeypatch, tmp_path, _full_pilot_import())
        report = json.loads(out.read_text())
        assert report["passed"] is True
        definition = report["definition_grounding"]
        assert definition["metaclass"] == "VerificationCaseDefinition"
        grounding = definition["grounding"]
        assert grounding["target"] == LIBRARY_DEFINITION_ANCHOR
        assert grounding["provenance"] == "implied"
        assert definition["provenance"] == "implied"
        assert grounding["mechanism"] in {"inline-reference", "external-reference"}
        assert grounding["uri"].endswith("VerificationCases.sysml")
        # The metaclass is a string field; the grounding is a structured
        # witness — never the same evidence collapsed into one another.
        assert isinstance(definition["metaclass"], str)
        assert isinstance(grounding, dict) and grounding["witness_id"]

    def test_usage_grounding_shape(self, tmp_path, monkeypatch):
        """VerificationCaseUsage + authored typing to the DE4SDV definition +
        implied Subsetting witness to VerificationCases::verificationCases."""
        out, _ = _run_readback(monkeypatch, tmp_path, _full_pilot_import())
        report = json.loads(out.read_text())
        assert report["passed"] is True
        assert report["binding_completeness"] == "complete"
        for index in range(1, 7):
            short = f"VC-AEBS-009D-{index:02d}"
            entry = report["usage_grounding"][short]
            assert entry["api_metaclass"] == "VerificationCaseUsage", short
            assert entry["completeness"] == "complete", short
            assert entry["definition_witness"]["kind"] == "FeatureTyping", short
            assert entry["definition_witness"]["target"] == DEFINITION_ELEMENT_ID
            assert entry["definition_witness_provenance"] == "explicit"
            grounding = entry["library_grounding_witness"]
            assert grounding["target"] == LIBRARY_USAGE_SET_ANCHOR, short
            assert entry["library_grounding_provenance"] == "implied"
            assert grounding["provenance"] == "implied"
            assert grounding["uri"].endswith("VerificationCases.sysml")

    def test_objective_chain_witnesses_in_readback(self, tmp_path, monkeypatch):
        """The verified-objective proof contract: requirement references
        carried by RequirementVerificationMembership witnesses on the
        definition objective, inherited by every usage."""
        out, _ = _run_readback(monkeypatch, tmp_path, _full_pilot_import())
        report = json.loads(out.read_text())
        assert report["passed"] is True
        assert set(report["witnesses_per_usage"]) == {
            f"VC-AEBS-009D-{index:02d}" for index in range(1, 7)
        }
        assert set(report["witnesses_per_usage"].values()) == {3}
        assert set(report["subjects_per_usage"].values()) == {1}

    def test_objective_chain_resolves_through_traversal(self):
        """RequirementVerificationMembership + verified requirement reference +
        owner/objective chain resolving to a VerificationCaseDefinition."""
        requirement = _requirement("req-1")
        hops = _traverse(requirement, _objective_chain_elements())
        assert len(hops) == 1
        hop = hops[0]
        assert hop.predicate == "verifiedBy"
        assert hop.strategy == "verification-membership"
        assert hop.semantic_strength == "native-verification"
        assert hop.target["@id"] == "vc-def-1"
        assert hop.api_object["@id"] == "rvm-1"

    def test_usage_owned_membership_resolves_to_usage_case(self):
        requirement = _requirement("req-1")
        elements = [
            requirement,
            _verification_case("vc-use-1", "VerificationCaseUsage"),
            _rvm("rvm-1", "vc-use-1", "req-1"),
        ]
        hops = _traverse(requirement, elements)
        assert len(hops) == 1
        assert hops[0].target["@id"] == "vc-use-1"

    def test_verified_requirement_property_form_resolves(self):
        """The serializer's alternate anchor form: the membership carries the
        verified requirement in ``verifiedRequirement`` (no memberElement)."""
        requirement = _requirement("req-1")
        elements = [
            requirement,
            _verification_case("vc-1"),
            {
                "@id": "rvm-1",
                "@type": "RequirementVerificationMembership",
                "owningRelatedElement": {"@id": "vc-1"},
                "verifiedRequirement": {"@id": "req-1"},
            },
        ]
        hops = _traverse(requirement, elements)
        assert len(hops) == 1
        assert hops[0].api_object["@id"] == "rvm-1"


# ---------------------------------------------------------------------------
# Negative semantic laws — none of these is sufficient evidence
# ---------------------------------------------------------------------------


class TestNegativeSemanticLaws:
    def test_law1_usage_metaclass_without_library_grounding(
        self, tmp_path, monkeypatch
    ):
        """A VerificationCaseUsage with the right metaclass and the authored
        definition typing but NO implied Subsetting witness is not grounded."""
        elements = [
            element
            for element in _full_pilot_import()
            if element.get("@id") != USAGE_01_SUBSETTING_EDGE_ID
        ]
        out, exit_code = _run_readback(monkeypatch, tmp_path, elements)
        report = json.loads(out.read_text())
        assert report["passed"] is False
        assert exit_code == 1
        assert any("implied Subsetting" in failure for failure in report["failures"])
        entry = report["usage_grounding"]["VC-AEBS-009D-01"]
        assert entry["api_metaclass"] == "VerificationCaseUsage"
        assert entry["completeness"] == "incomplete"

    def test_law2_definition_metaclass_without_library_grounding(
        self, tmp_path, monkeypatch
    ):
        """A VerificationCaseDefinition with the right metaclass but NO
        implied Subclassification witness is not grounded: UG-28."""
        elements = [
            element
            for element in _full_pilot_import()
            if element.get("@id") != DEFINITION_GROUNDING_EDGE_ID
        ]
        out, exit_code = _run_readback(monkeypatch, tmp_path, elements)
        report = json.loads(out.read_text())
        assert report["passed"] is False
        assert exit_code == 1
        assert any(
            "implied Subclassification" in failure for failure in report["failures"]
        )
        definition = report["definition_grounding"]
        assert definition["metaclass"] == "VerificationCaseDefinition"
        assert definition["grounding"] is None

    def test_law3_anchors_without_authored_definition_typing(
        self, tmp_path, monkeypatch
    ):
        """Correct library anchors are not enough: without the authored
        DE4SDV usage -> definition relationship the usage is ungrounded."""
        elements = [
            element
            for element in _full_pilot_import()
            if element.get("@id") != USAGE_01_TYPING_EDGE_ID
        ]
        out, exit_code = _run_readback(monkeypatch, tmp_path, elements)
        report = json.loads(out.read_text())
        assert report["passed"] is False
        assert exit_code == 1
        assert any(
            "no FeatureTyping witness" in failure for failure in report["failures"]
        )
        # Anchors and the implied library edge were still present.
        assert not any(
            "library anchors missing" in failure for failure in report["failures"]
        )
        entry = report["usage_grounding"]["VC-AEBS-009D-01"]
        assert entry["library_grounding_witness"] is not None

    def test_law4_rvm_owner_chain_without_case_fails(self):
        """A RequirementVerificationMembership whose owner chain never reaches
        a VerificationCaseUsage/Definition yields no hop."""
        requirement = _requirement("req-1")
        elements = [
            requirement,
            _verification_case("vc-1"),
            {
                "@id": "objective-1",
                "@type": "RequirementUsage",
                "declaredName": "evidenceObjective",
            },
            {
                "@id": "part-1",
                "@type": "PartUsage",
                "declaredName": "notAVerificationCase",
            },
            {
                "@id": "om-1",
                "@type": "ObjectiveMembership",
                "owningRelatedElement": {"@id": "part-1"},
                "memberElement": {"@id": "objective-1"},
            },
            _rvm("rvm-1", "objective-1", "req-1"),
        ]
        assert _traverse(requirement, elements) == []

    def test_law5_wrong_library_anchor_fails(self, tmp_path, monkeypatch):
        """A toolchain-implied edge that targets an id other than the recorded
        library anchor fails closed (no fallback to ''some library element'')."""
        elements = _full_pilot_import()
        wrong = "11111111-1111-4111-8111-111111111111"
        for element in elements:
            if element.get("@id") == DEFINITION_GROUNDING_EDGE_ID:
                element["superclassifier"] = {
                    "@id": wrong,
                    "@uri": element["superclassifier"]["@uri"],
                }
                element["general"] = {
                    "@id": wrong,
                    "@uri": element["general"]["@uri"],
                }
        out, exit_code = _run_readback(monkeypatch, tmp_path, elements)
        report = json.loads(out.read_text())
        assert report["passed"] is False
        assert exit_code == 1
        assert any(
            "implied Subclassification" in failure for failure in report["failures"]
        )
        # The recorded anchors themselves were present: the edge targeted a
        # wrong id, which is exactly the rejection under test.
        assert report["library_anchors"]["VerificationCases::VerificationCase"] == (
            LIBRARY_DEFINITION_ANCHOR
        )

    def test_law6_wrong_library_uri_fails(self, tmp_path, monkeypatch):
        """The implied Subsetting carries the right anchor id but a uri into a
        different document: grounding fails closed."""
        elements = _full_pilot_import()
        wrong_uri = (
            "file:///opt/hostedtoolcache/Python/3.12/site-packages/_syside/"
            "sysml.library/Systems%20Library/Requirements.sysml"
        )
        for element in elements:
            if element.get("@id") == USAGE_01_SUBSETTING_EDGE_ID:
                element["subsettedFeature"] = {
                    "@id": LIBRARY_USAGE_SET_ANCHOR,
                    "@uri": wrong_uri,
                }
        out, exit_code = _run_readback(monkeypatch, tmp_path, elements)
        report = json.loads(out.read_text())
        assert report["passed"] is False
        assert exit_code == 1
        assert any("implied Subsetting" in failure for failure in report["failures"])

    def test_law7_name_only_correspondence_fails(self):
        """Two requirements with the SAME declaredName: only the identity that
        the membership actually anchors on resolves — no name-based fallback."""
        queried = _requirement("req-1", name="evidenceContractSharedName")
        namesake = _requirement("req-2", name="evidenceContractSharedName")
        case = _verification_case("vc-1")
        rvm = _rvm("rvm-1", "vc-1", "req-2")
        assert _traverse(queried, [queried, namesake, case, rvm]) == []
        # Control: the identity that the membership references does resolve.
        assert len(_traverse(namesake, [queried, namesake, case, rvm])) == 1

    def test_law8_generic_dependency_fails(self):
        """A generic Dependency Requirement -> VerificationCase establishes no
        verifiedBy hop (UG-05-class discrimination)."""
        requirement = _requirement("req-1")
        case = _verification_case("vc-1")
        elements = [
            requirement,
            case,
            {
                "@id": "dep-1",
                "@type": "Dependency",
                "client": {"@id": "req-1"},
                "supplier": {"@id": "vc-1"},
            },
            {
                "@id": "dep-2",
                "@type": "Dependency",
                "source": {"@id": "req-1"},
                "target": {"@id": "vc-1"},
            },
        ]
        assert _traverse(requirement, elements) == []

    def test_law9_subject_membership_fails(self):
        """A SubjectMembership can substitute for nothing here."""
        requirement = _requirement("req-1")
        case = _verification_case("vc-1")
        elements = [
            requirement,
            case,
            {
                "@id": "sm-1",
                "@type": "SubjectMembership",
                "owningRelatedElement": {"@id": "req-1"},
                "memberElement": {"@id": "vc-1"},
            },
        ]
        assert _traverse(requirement, elements) == []

    def test_law10_verification_method_metadata_fails(self):
        """VerificationMethod metadata on the case does not create the
        verification-objective relationship."""
        requirement = _requirement("req-1")
        case = _verification_case("vc-1")
        elements = [
            requirement,
            case,
            {
                "@id": "mem-1",
                "@type": "OwningMembership",
                "owningRelatedElement": {"@id": "vc-1"},
                "memberElement": {"@id": "meta-1"},
            },
            {
                "@id": "meta-1",
                "@type": "MetadataUsage",
                "declaredName": "VerificationMethod",
                "owningRelationship": {"@id": "mem-1"},
            },
        ]
        assert _traverse(requirement, elements) == []

    def test_law11_retained_evidence_presence_is_not_semantic_proof(self, decisions):
        """Retained evidence — however strong — is not the relationship, and
        the retained Lane B run does not promote either row."""
        # Mechanism: retained-record-shaped elements plus even a Dependency
        # into the requirement still yield no hop.
        requirement = _requirement("req-1")
        case = _verification_case("vc-1")
        elements = [
            requirement,
            case,
            {
                "@id": "rec-1",
                "@type": "ItemUsage",
                "declaredName": "retainedExecutionRecord",
            },
            {
                "@id": "fv-1",
                "@type": "FeatureValue",
                "owningRelatedElement": {"@id": "rec-1"},
                "memberElement": {"@id": "lit-1"},
            },
            {
                "@id": "lit-1",
                "@type": "LiteralString",
                "value": "run-20260727T222325Z",
            },
            {
                "@id": "dep-1",
                "@type": "Dependency",
                "source": {"@id": "rec-1"},
                "target": {"@id": "req-1"},
            },
        ]
        assert _traverse(requirement, elements) == []
        # Governance: the retained exact-toolchain run stays supporting
        # evidence only; the rows are not promoted and carry no closure ref.
        for name in C2_IDENTITIES:
            row = decisions["entries"][name]
            assert row["evidence_state"] == "parity-reviewed", name
            assert row["closure_evidence_ref"] is None, name

    def test_law12_outcome_metadata_does_not_create_the_relationship(self):
        """PASS-like/evaluation metadata around the case is not the semantic
        relationship: the relationship exists independently of outcome."""
        requirement = _requirement("req-1")
        case = _verification_case("vc-def-1", "VerificationCaseDefinition")
        elements = [
            requirement,
            case,
            {
                "@id": "out-1",
                "@type": "ItemUsage",
                "declaredName": "replayedEvaluation",
            },
            {
                "@id": "fv-1",
                "@type": "FeatureValue",
                "owningRelatedElement": {"@id": "out-1"},
                "memberElement": {"@id": "verdict-pass"},
            },
            {
                "@id": "verdict-pass",
                "@type": "EnumerationLiteral",
                "declaredName": "pass",
            },
            {
                "@id": "mem-2",
                "@type": "OwningMembership",
                "owningRelatedElement": {"@id": "vc-def-1"},
                "memberElement": {"@id": "out-1"},
            },
        ]
        assert _traverse(requirement, elements) == []
        # Positive control on the SAME elements plus the native membership:
        # the relationship resolves exactly through the membership, showing
        # the outcome-shaped elements neither add nor block the semantics.
        with_membership = elements + [_rvm("rvm-1", "out-1", "req-1")]
        assert len(_traverse(requirement, with_membership)) == 1


# ---------------------------------------------------------------------------
# Traversal fail-closed confirmation (no behavior change, single traversal)
# ---------------------------------------------------------------------------


class TestTraversalFailClosed:
    def test_only_configured_membership_types_count(self):
        requirement = _requirement("req-1")
        case = _verification_case("vc-1")
        elements = [
            requirement,
            case,
            {
                "@id": "plain-1",
                "@type": "Membership",
                "owningRelatedElement": {"@id": "vc-1"},
                "memberElement": {"@id": "req-1"},
            },
            {
                "@id": "fm-1",
                "@type": "FeatureMembership",
                "owningRelatedElement": {"@id": "vc-1"},
                "memberElement": {"@id": "req-1"},
            },
        ]
        assert _traverse(requirement, elements) == []

    def test_foreign_memberships_are_ignored(self):
        req_a = _requirement("req-1")
        req_b = _requirement("req-2", name="evidenceContractOther")
        case = _verification_case("vc-1")
        elements = [req_a, req_b, case, _rvm("rvm-1", "vc-1", "req-2")]
        assert _traverse(req_a, elements) == []
        assert len(_traverse(req_b, elements)) == 1

    def test_wrong_owner_type_does_not_become_a_case(self):
        requirement = _requirement("req-1")
        owner = {"@id": "part-1", "@type": "PartUsage", "declaredName": "bench"}
        elements = [requirement, owner, _rvm("rvm-1", "part-1", "req-1")]
        assert _traverse(requirement, elements) == []

    def test_missing_owner_chain_returns_no_hop(self):
        requirement = _requirement("req-1")
        case = _verification_case("vc-1")
        elements = [
            requirement,
            case,
            {
                "@id": "rvm-1",
                "@type": "RequirementVerificationMembership",
                "memberElement": {"@id": "req-1"},
            },
        ]
        assert _traverse(requirement, elements) == []

    def test_verification_membership_configuration_locked(self):
        """The reviewed representation configuration is pinned exactly; the
        traversal is not broadened and there is no second verification
        traversal."""
        mapping = _contract().relationship_mapping("verifiedBy")
        assert mapping.configuration == {
            "membership_types": ["RequirementVerificationMembership"],
            "element_types": ["VerificationCaseUsage", "VerificationCaseDefinition"],
            "owner_membership_types": [
                "FeatureMembership",
                "OwningMembership",
                "ObjectiveMembership",
                "RequirementVerificationMembership",
            ],
            "reference_property": "verifiedRequirement",
            "direction": "reverse",
        }
        assert mapping.semantic_strength == "native-verification"
        source = (REPO_ROOT / "de4sdv/semantic/traversal.py").read_text(
            encoding="utf-8"
        )
        assert source.count('"verification-membership"') == 1
        assert source.count("def _verification_membership_hops") == 1


# ---------------------------------------------------------------------------
# Committed model shapes the grounding is proven against
# ---------------------------------------------------------------------------


class TestCommittedModelShapes:
    def test_pilot_definition_and_usage_authored_shapes(self):
        """The DE4SDV verification definition/usages the Lane B grounding was
        proven against exist with authored typing in the committed model."""
        text = PILOT_MODEL.read_text(encoding="utf-8")
        declaration = (
            "verification def <'VC-AEBS-009D-DE'>ConsciousOverrideVerification"
        )
        block, bodyless = ai.declaration_block(text, declaration)
        assert block and not bodyless
        for index in range(1, 7):
            match = re.search(
                rf"verification <'VC-AEBS-009D-0{index}'>(\w+) "
                r": ConsciousOverrideVerification \{",
                text,
            )
            assert match, f"usage VC-AEBS-009D-0{index} missing authored typing"

    def test_pilot_objective_carries_verify_statements(self):
        """The definition objective carries the three requirement-verification
        statements (the authored form of RequirementVerificationMembership)."""
        text = PILOT_MODEL.read_text(encoding="utf-8")
        block, _ = ai.declaration_block(
            text,
            "verification def <'VC-AEBS-009D-DE'>ConsciousOverrideVerification",
        )
        assert "objective evidenceObjective {" in block
        assert len(re.findall(r"\bverify\b", block)) == 3
        assert len(re.findall(r"verify evidenceContract", block)) == 3
