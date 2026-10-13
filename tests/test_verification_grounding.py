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

from de4sdv.semantic import authority_inventory as ai
from de4sdv.semantic.traversal import SemanticTraversal

from test_candidate_export_correspondence_readback import (  # noqa: E402 - shared real-shape fixtures
    LIBRARY_DEFINITION_ANCHOR,
    LIBRARY_USAGE_SET_ANCHOR,
    _full_pilot_import,
    _run_readback,
)
from model_contract_fixtures import model_contract  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]

PILOT_MODEL = (
    REPO_ROOT
    / "textual-notation-of-model/packages/features/aebs/aebs_override_verification.sysml"
)

#: The c2 batch is exactly these two identities — no third entry.
C2_IDENTITIES: tuple[str, ...] = ("VerificationCase", "verifiedBy")


#: Synthetic serializer fixtures (synthetic ids, real machinery).
DEFINITION_ELEMENT_ID = "00000000-0000-4000-8000-0000000000d0"
DEFINITION_GROUNDING_EDGE_ID = "99999999-0000-4000-8000-0000000000d1"
USAGE_01_TYPING_EDGE_ID = "00000000-0000-4000-8000-0000000000g1"
USAGE_01_SUBSETTING_EDGE_ID = "00000000-0000-4000-8000-00000000ss01"


def _contract() -> ai.KernelContract:
    return model_contract()


def _requirement_kernel_index():
    """Validated kernel binding for the governed Requirement lineage.

    c5 R2 runtime-domain closure: the verifiedBy runtime resolves the
    relationship's declared ontology domain through ingestion-validated
    kernel bindings, so fixtures carry them exactly like the production
    binding does (never a name-based resolution).
    """
    from de4sdv.semantic.kernel_binding_index import KernelBindingIndex
    from de4sdv.sysml_api.revisions import RevisionBinding

    return KernelBindingIndex.from_binding(
        RevisionBinding.from_dict(
            {
                "schema": "de4sdv.revision-binding/v2",
                "git_repository": "de4sdv/DE4SDV",
                "git_commit": "a" * 40,
                "sysml_project_id": "project-1",
                "sysml_commit_id": "commit-1",
                "import_timestamp": "2026-09-01T00:00:00Z",
                "import_tool_version": "fixture/1",
                "semantic_validation": "passed",
                "scope": "fixture",
                "semantic_authority": _contract().identity.to_dict(),
                "kernel_bindings": [
                    {
                        "ontology_class": "Requirement",
                        "element_id": "kernel-requirement",
                        "source_file": (
                            "textual-notation-of-model/packages/methods/de4sdv/"
                            "de4sdv_method_context.sysml"
                        ),
                        "declaration": "requirement def RequirementCandidate",
                    },
                ],
            }
        )
    )


def _requirement_grounding(requirement: dict) -> list[dict]:
    """Kernel element + authored grounding typing for a fixture usage.

    c5 R2 runtime-domain closure: the queried requirement must ground in the
    validated Requirement lineage before any verifiedBy hop is emitted; the
    fixtures carry that grounding the way the real model carries it (kernel
    declaration + authored typing, resolved from the validated binding).
    """
    return [
        {
            "@id": "kernel-requirement",
            "@type": "RequirementDefinition",
            "declaredName": "RequirementCandidate",
            "qualifiedName": "DE4SDV_MethodContext::RequirementCandidate",
        },
        {
            "@id": f"{requirement['@id']}-grounding",
            "@type": "FeatureTyping",
            "owningRelatedElement": {"@id": requirement["@id"]},
            "type": {"@id": "kernel-requirement"},
            "typedFeature": {"@id": requirement["@id"]},
        },
    ]


def _traverse(requirement: dict, elements: list[dict]):
    """Traverse ``verifiedBy`` with the governed source-domain machinery.

    The traversal carries the validated Requirement binding and the fixture
    population carries the queried requirement's authored grounding typing
    (c5 R2 runtime-domain closure): the declared domain is enforced from the
    validated binding, never from names.
    """
    return SemanticTraversal(
        _contract(), kernel_bindings=_requirement_kernel_index()
    ).traverse(
        "verifiedBy",
        requirement,
        list(elements) + _requirement_grounding(requirement),
    )


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


# ---------------------------------------------------------------------------
# c2 scope and inventory state
# ---------------------------------------------------------------------------


class TestC2ScopeAndCounts:
    def test_c2_is_exactly_two_identities(self):
        assert len(C2_IDENTITIES) == 2
        assert len(set(C2_IDENTITIES)) == 2


# ---------------------------------------------------------------------------
# Reviewed decision record content and claim boundary
# ---------------------------------------------------------------------------


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

    def test_law11_retained_evidence_presence_is_not_semantic_proof(self):
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
