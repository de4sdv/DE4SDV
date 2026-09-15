"""O2.1 — Semantic Projection v1 / API Representation Profile v1 tests.

Covers the O2.1 bounded generation stage (Stage A: implementation
foundation; the canonical committed artifacts and the repository gate
registration are published in Stage B — see the design record):

1.  **positive scope**: exactly the seven settled c1 identities are generated,
    each exactly once, with model-derived semantic kind, definition
    documentation (witnessed), typed member structure, kernel-binding
    contract, standard-library base grounding, the projection-level claim
    contract (``projection_contract`` — concept-specific claim-boundary
    documentation remains model-derived where authored, and no generic claim
    policy is serialized per concept), and ``vocabulary-only`` support state;
    the tests run against the ACTUAL production model declarations (the
    generator's real input), not only synthetic fixtures;
2.  **machine-locked admission**: the admission manifest and the frozen code
    lock agree exactly (seven admitted; 13-identity sequencing union; no
    overlap with the excluded guard set); manifest drift fails closed;
3.  **negative scope**: the excluded identities (MethodEvaluationScope,
    DerivesFromNeed, the deferred O2.2/O2.3 set, the retired/blocked/
    rename-required set) never appear as O2.1 rows even though their
    representations are model-resident and discoverable;
4.  **adversarial fixtures** (A-I of the O2.1 specification): extra model
    vocabulary does not expand the output; a missing admitted declaration,
    ambiguous grounding, wrong declaration kind, missing documentation,
    unresolved member typing, and unsupported member forms all fail closed;
    the generator does not read O1 migration artifacts (a checkout without
    them generates identically, and decoy O1 data cannot manufacture a row);
5.  **Projection v0 compatibility**: v0 schemas, builders, and the K fixture
    projection are unchanged by the additive v1 module;
6.  **runtime independence**: no runtime module imports the v1 machinery or
    reads the v1 artifacts.

Stage B (artifact publication) additionally activates the committed-artifact
consistency tests and the ``check_repo`` gate-registration test; both require
the canonical artifacts and are deferred here by the squash-safe delivery
sequence (their intent is preserved — see the marker in this file and the
design record). No artifact-dependent test is silently skipped: in Stage A
the artifact-dependent tests are simply not registered yet.
"""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic import projection_v1 as pv
from de4sdv.semantic.kernel_contract import KernelContract, declaration_identity

REPO_ROOT = Path(__file__).resolve().parents[1]

CONFORMANCE_FILE = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_conformance.sysml"
PROCESS_FILE = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml"
MODEL_FILES = (CONFORMANCE_FILE, PROCESS_FILE)

O1_ARTIFACT_PATHS = (
    "docs/method-conformance/o1/semantic-authority-inventory.json",
    "docs/method-conformance/o1/authority-review-decisions.yaml",
    "docs/method-conformance/o1/phase1-inventory-review.md",
)

#: Layer-B reviewed-decision field names of the O1 inventory: governance
#: metadata that must NEVER leak into generated semantic rows.
O1_GOVERNANCE_FIELDS = (
    "authority_current",
    "authority_target",
    "evidence_state",
    "adoption_status",
    "transition_gate",
    "conditional_target",
    "disposition",
    "confidence",
    "stage",
    "unknowns",
    "required_evidence",
    "exact_fit_decision",
    "closure_evidence_ref",
    "semantic_text_equivalence",
)

#: O1 evidence-state values that are reviewed governance, not model semantics.
O1_EVIDENCE_VALUES = (
    "reviewed-equivalent",
    "parity-reviewed",
    "repository-evidenced",
    "exact-toolchain-validated",
    "privileged-closure-proven",
    "pinned-not-adopted",
)

#: Machine-locked negative scope (O2.1 specification): none of these may
#: appear as a new v1 O2.1 row.
O21_NEGATIVE_IDENTITIES = (
    "MethodEvaluationScope",
    "DerivesFromNeed",
    "VerificationCase",
    "hasSubject",
    "verifiedBy",
    "derivesRequirementFromNeed",
    "derivedRequirementsOfNeed",
    "hasRelevantArchitecture",
    "realizedBy",
    "specifiesFunction",
    "hasRelevantEvidenceContract",
    "derivesNeedFromConcern",
)

#: The real production declarations: member structure pinned from the merged
#: baseline model files (the c1 final documentation state).
EXPECTED_MEMBERS: dict[str, list[tuple[str, str]]] = {
    "MethodContractObligation": [
        ("obligationId", "String"),
        ("phase", "MethodPhase"),
        ("subjectSelector", "String"),
        ("applicability", "String"),
        ("minimumPopulation", "Natural"),
        ("permittedEmpty", "Boolean"),
        ("predicate", "String"),
        ("targetFilter", "String"),
        ("cardinalityMinimum", "Natural"),
        ("cardinalityMaximum", "Natural"),
        ("required", "Boolean"),
        ("evaluationSource", "EvaluationSourceKind"),
        ("attestationPolicyRef", "String"),
        ("claimBoundary", "String"),
    ],
    "EvaluationScopeMembership": [
        ("scopeId", "String"),
        ("subjectId", "String"),
        ("contributes", "Boolean"),
    ],
    "TestedScopeDeclaration": [
        ("executionHead", "String"),
        ("profileIdentities", "String"),
    ],
    "RetainedExecutionRecordReference": [
        ("recordId", "String"),
        ("artifactPath", "String"),
        ("sha256", "String"),
        ("runId", "String"),
    ],
    "AcceptanceAttestationReference": [
        ("policyRef", "String"),
        ("decisionRegistryPath", "String"),
    ],
}

EXPECTED_LITERALS: dict[str, list[str]] = {
    "MethodPhase": [
        "phase0_incrementFraming",
        "phase1_concernFraming",
        "phase2_operationalContext",
        "phase3_capabilityClassification",
        "phase4_needs",
        "phase5_requirements",
        "phase6_functionalArchitecture",
        "phase7_logicalArchitecture",
        "phase8_physicalRealization",
        "phase9_variabilityConfiguration",
        "phase10_vvEvidence",
        "phase11_publication",
        "phase12_baselineNextSlice",
    ],
    "EvaluationSourceKind": [
        "pinnedModelRecord",
        "pinnedRepositoryArtifact",
        "liveDeliveryAdapter",
    ],
}

EXPECTED_METACLASS: dict[str, str] = {
    "MethodPhase": "EnumerationDefinition",
    "MethodContractObligation": "ItemDefinition",
    "EvaluationScopeMembership": "ItemDefinition",
    "EvaluationSourceKind": "EnumerationDefinition",
    "TestedScopeDeclaration": "ItemDefinition",
    "RetainedExecutionRecordReference": "ItemDefinition",
    "AcceptanceAttestationReference": "ItemDefinition",
}

#: Direct-depth documentation counts of the c1 final model state (matches the
#: O1 c1 measured observations: the five `differs` rows carry their attribute
#: documentation at the declaration body's direct lexical depth).
EXPECTED_DOC_COUNTS: dict[str, int] = {
    "MethodPhase": 1,
    "MethodContractObligation": 12,
    "EvaluationScopeMembership": 4,
    "EvaluationSourceKind": 1,
    "TestedScopeDeclaration": 3,
    "RetainedExecutionRecordReference": 1,
    "AcceptanceAttestationReference": 3,
}


@pytest.fixture(scope="module")
def pair() -> dict:
    """The real artifacts, generated against the committed checkout."""
    return pv.build_pair(REPO_ROOT)


@pytest.fixture()
def stubbed_gate(monkeypatch):
    """Fixture repos are not Git checkouts: stub the containment gate.

    The real gate is exercised against the committed repository by the
    module-level ``pair`` fixture and ``TestCommittedArtifacts``; synthetic
    fixtures test derivation fail-closed behavior.
    """
    monkeypatch.setattr(
        pv, "verify_source_revision_contains_inputs", lambda *a, **k: None
    )


def _remove_declaration(text: str, declaration: str) -> str:
    """Remove one whole braced declaration statement (keyword through brace).

    Uses the generator's own strict locator so the mutation removes exactly
    what the generator would have consumed: the declaration keyword and its
    adjacent body. A body-only removal would leave a keyword without a body
    (which the strict locator already rejects as malformed).
    """
    located = pv.locate_declaration(text, declaration)
    assert located is not None, declaration
    match_start, brace_start, block = located
    close = brace_start + len(block) - 1
    return text[:match_start] + text[close + 1:]


def _fixture_root(
    tmp_path: Path,
    *,
    contract_mutator=None,
    file_mutators: dict | None = None,
    manifest_mutator=None,
    with_decoy_o1: bool = False,
) -> Path:
    """A synthetic checkout containing exactly the generator's inputs."""
    root = tmp_path / "repo"
    for rel in (pv.ONTOLOGY_PATH, pv.ADMISSION_PATH, *pv.BOUND_INPUT_PROGRAM_PATHS):
        destination = root / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((REPO_ROOT / rel).read_bytes())
    contract = yaml.safe_load((REPO_ROOT / pv.ONTOLOGY_PATH).read_text(encoding="utf-8"))
    if contract_mutator is not None:
        contract_mutator(contract)
    (root / pv.ONTOLOGY_PATH).write_text(
        yaml.safe_dump(contract, sort_keys=False), encoding="utf-8"
    )
    for rel in MODEL_FILES:
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        if file_mutators and rel in file_mutators:
            text = file_mutators[rel](text)
        destination = root / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")
    if manifest_mutator is not None:
        manifest = yaml.safe_load(
            (REPO_ROOT / pv.ADMISSION_PATH).read_text(encoding="utf-8")
        )
        manifest_mutator(manifest)
        (root / pv.ADMISSION_PATH).write_text(
            yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
        )
    if with_decoy_o1:
        decoy = root / "docs/method-conformance/o1/semantic-authority-inventory.json"
        decoy.parent.mkdir(parents=True, exist_ok=True)
        decoy.write_text(
            json.dumps(
                {
                    "note": "decoy O1 data claiming accepted identities",
                    "entries": [
                        {"identity": identity, "reviewed": {"authority_current": "legacy-yaml"}}
                        for identity in pv.O21_ADMITTED_IDENTITIES
                    ],
                }
            ),
            encoding="utf-8",
        )
    return root


# ---------------------------------------------------------------------------
# 1. Positive scope (actual production declarations)
# ---------------------------------------------------------------------------


class TestPositiveScope:
    def test_exactly_seven_identities_in_order_once_each(self, pair) -> None:
        identities = [row["identity"] for row in pair["projection"]["concepts"]]
        assert identities == list(pv.O21_ADMITTED_IDENTITIES)
        assert len(set(identities)) == 7

    @pytest.mark.parametrize("identity", list(pv.O21_ADMITTED_IDENTITIES))
    def test_semantic_kind_and_grounding_contract(self, pair, identity) -> None:
        row = _row(pair, identity)
        semantic_kind = "enumeration" if identity in EXPECTED_LITERALS else "item"
        assert row["semantic_kind"] == semantic_kind
        contract = row["grounding"]["kernel_binding_contract"]
        expected_file = CONFORMANCE_FILE if identity != "MethodPhase" else PROCESS_FILE
        assert contract["source_file"] == expected_file
        assert contract["declaration"] in (
            f"enum def {identity}",
            f"item def {identity}",
        )
        assert contract["api_metaclass"] == EXPECTED_METACLASS[identity]
        assert "ingestion-validated kernel binding" in contract["resolution"]
        base = row["grounding"]["standard_library_base"]
        expected_base = (
            "Kernel Semantic Library (Base.kerml)"
            if semantic_kind == "enumeration"
            else "Systems Model Library (Items.sysml)"
        )
        assert base["library"] == expected_base
        assert base["provenance"] == "implied"

    @pytest.mark.parametrize("identity", list(pv.O21_ADMITTED_IDENTITIES))
    def test_definition_documentation_witnessed_nonempty(self, pair, identity) -> None:
        row = _row(pair, identity)
        definition = row["definition"]
        assert definition["documentation"].strip()
        witness = definition["documentation_witness"]
        assert witness["declaration"] in (
            f"enum def {identity}",
            f"item def {identity}",
        )
        assert witness["doc_count"] == EXPECTED_DOC_COUNTS[identity]

    @pytest.mark.parametrize("identity", list(EXPECTED_MEMBERS))
    def test_typed_attribute_structure(self, pair, identity) -> None:
        row = _row(pair, identity)
        assert row["structure"]["members_kind"] == "typed-attributes"
        members = row["structure"]["members"]
        assert [(m["name"], _type_label(m["type"])) for m in members] == [
            (name, type_name) for name, type_name in EXPECTED_MEMBERS[identity]
        ]
        # Case 5 (production declarations): every current O2.1 attribute
        # authors NO default, so the absence representation appears — an
        # absent default is never rendered as an authored empty-string value.
        for member in members:
            assert "default_expression" in member
            assert member["default_expression"] is None

    @pytest.mark.parametrize("identity", list(EXPECTED_LITERALS))
    def test_enumeration_literal_structure(self, pair, identity) -> None:
        row = _row(pair, identity)
        assert row["structure"]["members_kind"] == "enumeration-literals"
        members = row["structure"]["members"]
        assert [m["name"] for m in members] == EXPECTED_LITERALS[identity]
        assert all(m["documentation"].strip() for m in members)

    def test_governed_class_member_typing_is_identity_not_name(self, pair) -> None:
        row = _row(pair, "MethodContractObligation")
        types = {m["name"]: m["type"] for m in row["structure"]["members"]}
        assert types["phase"] == {"kind": "governed-class", "identity": "MethodPhase"}
        assert types["evaluationSource"] == {
            "kind": "governed-class",
            "identity": "EvaluationSourceKind",
        }
        assert types["obligationId"] == {
            "kind": "external-library-type",
            "name": "String",
            "library": "Kernel Data Type Library (ScalarValues.kerml)",
        }

    def test_projection_contract_is_projection_level_not_per_concept(self, pair) -> None:
        """The claim contract is schema/projection metadata: it lives once at
        the projection level and is NOT serialized as per-concept semantics."""
        projection = pair["projection"]
        assert projection["projection_contract"] == pv.PROJECTION_CONTRACT
        for row in projection["concepts"]:
            assert "claim_boundary" not in row
            assert "model_external_boundary" not in row
            # the generic policy text never masquerades inside a concept row
            row_text = json.dumps(row)
            assert "does_not_assert" not in row_text
            assert "obligation satisfaction" not in row_text

    def test_support_state_remains_vocabulary_only(self, pair) -> None:
        for row in pair["projection"]["concepts"]:
            assert row["support_state"] == "vocabulary-only"

    def test_projection_contract_contents(self, pair) -> None:
        contract = pair["projection"]["projection_contract"]
        assert contract["does_not_assert"] == [
            "obligation satisfaction",
            "method-phase completion",
            "acceptance or approval decision",
            "evidence validity or freshness",
            "tested-scope equality",
            "evaluation success",
        ]
        assert "vocabulary/schema definitions only" in contract["semantic_scope"]
        assert "derived from the governed model representation" in contract[
            "derivation_rule"
        ]
        assert "remain external" in contract["external_artifact_treatment"]
        assert "not authority activation" in contract["runtime_boundary"]

    def test_no_support_promotion_path_exists(self) -> None:
        """No promotion input: v1 builders take no attestation/verification
        flag. The bare-boolean promotion attempt is a removal-proof site
        (registered in the K guard's designated set): it fails with TypeError,
        exactly like the removed v0 boolean."""
        import inspect

        for function in (
            pv.build_pair,
            pv.build_projection_v1,
            pv.build_representation_profile_v1,
        ):
            parameters = set(inspect.signature(function).parameters)
            assert "closure_attestation" not in parameters
        with pytest.raises(TypeError):
            pv.build_projection_v1(REPO_ROOT, witness_closure_verified=True)

    def test_revision_binding_separates_software_and_model_revisions(self, pair) -> None:
        binding = pair["projection"]["binding"]
        assert re.fullmatch(r"[0-9a-f]{40}", binding["source_revision"])
        assert binding["artifact_commit"] is None
        generation = binding["generation_software"]["program_inputs"]
        semantic = binding["semantic_model_revision"]["model_inputs"]
        assert semantic == sorted(MODEL_FILES)
        assert set(generation).isdisjoint(semantic)
        assert binding["api_binding"]["status"] == "unclaimed"
        for path in (*generation, *semantic):
            assert path in binding["bound_inputs"]
        assert binding["admission_manifest"]["path"] == pv.ADMISSION_PATH
        assert binding["ontology_contract_locator"]["path"] == pv.ONTOLOGY_PATH

    def test_scope_block_echoes_admission_boundary(self, pair) -> None:
        scope = pair["projection"]["scope"]
        assert scope["admitted"] == list(pv.O21_ADMITTED_IDENTITIES)
        assert scope["sequencing"]["o2.1"] == list(pv.O21_ADMITTED_IDENTITIES)
        excluded_ids = [entry["identity"] for entry in scope["excluded"]]
        assert set(excluded_ids) == set(pv.O21_EXCLUDED_IDENTITIES)
        assert all(entry["reason"].strip() for entry in scope["excluded"])

    def test_deterministic_serialization(self, pair) -> None:
        again = pv.build_pair(REPO_ROOT)
        assert pv.canonical_json(again["projection"]) == pv.canonical_json(
            pair["projection"]
        )
        assert pv.canonical_json(again["profile"]) == pv.canonical_json(
            pair["profile"]
        )

    def test_no_o1_governance_field_leaks_into_semantic_rows(self, pair) -> None:
        for row in pair["projection"]["concepts"]:
            keys = set(_all_keys(row))
            overlap = keys & set(O1_GOVERNANCE_FIELDS)
            assert not overlap, f"{row['identity']}: O1 governance keys leaked: {overlap}"
            text = json.dumps(row)
            for value in O1_EVIDENCE_VALUES:
                assert value not in text, (
                    f"{row['identity']}: O1 governance value {value!r} leaked "
                    "into semantic row"
                )

    def test_artifacts_do_not_reference_o1_artifacts(self, pair) -> None:
        projection_text = pv.canonical_json(pair["projection"])
        profile_text = pv.canonical_json(pair["profile"])
        for path in O1_ARTIFACT_PATHS:
            assert path not in projection_text
            assert path not in profile_text
        for path in pair["projection"]["binding"]["bound_inputs"]:
            assert "method-conformance/o1" not in path

    def test_profile_entries_match_projection(self, pair) -> None:
        entries = {entry["for_concept"]: entry for entry in pair["profile"]["profiles"]}
        assert set(entries) == set(pv.O21_ADMITTED_IDENTITIES)
        for row in pair["projection"]["concepts"]:
            entry = entries[row["identity"]]
            assert entry["binding_contract_echo"] == row["grounding"][
                "kernel_binding_contract"
            ]
            expected_class = (
                "enumeration-definition"
                if row["semantic_kind"] == "enumeration"
                else "item-definition"
            )
            assert entry["representation_class"] == expected_class
            assert entry["witness_forms"]

    def test_profile_carries_mechanics_not_meaning(self, pair) -> None:
        """Representation mechanics must not restate semantic content."""
        profile_text = pv.canonical_json(pair["profile"])
        for row in pair["projection"]["concepts"]:
            assert row["definition"]["documentation"] not in profile_text
            for member in row["structure"]["members"]:
                documentation = member.get("documentation", "")
                if documentation:
                    assert documentation not in profile_text

    def test_profile_evidence_basis_is_scoped(self, pair) -> None:
        basis = pair["profile"]["evidence_basis"]
        assert basis["run"] == "10195168006"
        assert "NOT a semantic source" in basis["scope"]
        contract = pair["profile"]["representation_contract"]
        targets = contract["external_library_type_targets"]["targets"]
        assert set(targets) == {"String", "Natural", "Boolean"}
        assert contract["serializer_importer_compatibility"]["known_omissions"] == []
        assert contract["identity_resolution"]["prohibited_fallbacks"]

    def test_duplicate_declaration_scan_is_exact_once(self) -> None:
        """Each admitted declaration occurs exactly once in its file."""
        contract = KernelContract.load(REPO_ROOT / pv.ONTOLOGY_PATH)
        for identity in pv.O21_ADMITTED_IDENTITIES:
            mapping = contract.mapping(identity)
            text = (REPO_ROOT / mapping.file).read_text(encoding="utf-8")
            kind, _, name = mapping.declaration.partition(" def ")
            occurrences = len(
                re.findall(
                    r"(?m)^[ \t]*(?:(?:public|private|protected)\s+)?"
                    r"(?:abstract\s+)?"
                    + re.escape(kind)
                    + r"\s+def\s+"
                    + re.escape(name)
                    + r"\b",
                    text,
                )
            )
            assert occurrences == 1


class TestDefaultExpressionSemantics:
    """Case matrix for authored default expressions (O2.1 correction B):

    ``no default != authored empty-string default != false != 0``. Absence is
    ``null``; an authored expression is preserved verbatim and never
    evaluated.
    """

    def _fixture_members(
        self, tmp_path, stubbed_gate, extra_attribute_lines: str
    ) -> dict:
        def file_mutator(text: str) -> str:
            marker = "    attribute contributes : Boolean;"
            assert marker in text
            return text.replace(marker, marker + "\n" + extra_attribute_lines)

        root = _fixture_root(
            tmp_path, file_mutators={CONFORMANCE_FILE: file_mutator}
        )
        artifacts = pv.build_pair(root, source_revision="0" * 40)
        row = next(
            r
            for r in artifacts["projection"]["concepts"]
            if r["identity"] == "EvaluationScopeMembership"
        )
        return {m["name"]: m for m in row["structure"]["members"]}

    def test_case1_no_default_stays_absent(self, tmp_path, stubbed_gate) -> None:
        members = self._fixture_members(
            tmp_path, stubbed_gate, "    attribute testNoDefault : String;"
        )
        assert members["testNoDefault"]["default_expression"] is None

    def test_case2_explicit_empty_string_is_distinguishable(
        self, tmp_path, stubbed_gate
    ) -> None:
        members = self._fixture_members(
            tmp_path, stubbed_gate, '    attribute testEmpty : String = "";'
        )
        # the AUTHORED empty-string literal, distinct from absence
        assert members["testEmpty"]["default_expression"] == '""'
        assert members["testEmpty"]["default_expression"] is not None
        # absence remains absence right next to it
        assert members["contributes"]["default_expression"] is None

    def test_case3_explicit_boolean_preserved(self, tmp_path, stubbed_gate) -> None:
        members = self._fixture_members(
            tmp_path, stubbed_gate, "    attribute testBool : Boolean = false;"
        )
        assert members["testBool"]["default_expression"] == "false"

    def test_case4_explicit_numeric_preserved(self, tmp_path, stubbed_gate) -> None:
        members = self._fixture_members(
            tmp_path, stubbed_gate, "    attribute testNum : Natural = 0;"
        )
        assert members["testNum"]["default_expression"] == "0"

    def test_interior_whitespace_of_expression_preserved(
        self, tmp_path, stubbed_gate
    ) -> None:
        members = self._fixture_members(
            tmp_path, stubbed_gate, '    attribute testSpacing : String = "a  b";'
        )
        assert members["testSpacing"]["default_expression"] == '"a  b"'

    def test_malformed_empty_expression_fails_closed(
        self, tmp_path, stubbed_gate
    ) -> None:
        with pytest.raises(pv.ProjectionV1Error, match="empty expression"):
            self._fixture_members(
                tmp_path, stubbed_gate, "    attribute testBad : String = ;"
            )


# ---------------------------------------------------------------------------
# 2. Machine-locked admission boundary
# ---------------------------------------------------------------------------


class TestAdmissionLock:
    def test_frozen_lock_and_sequencing(self) -> None:
        assert pv.O21_ADMITTED_IDENTITIES == (
            "MethodPhase",
            "MethodContractObligation",
            "EvaluationScopeMembership",
            "EvaluationSourceKind",
            "TestedScopeDeclaration",
            "RetainedExecutionRecordReference",
            "AcceptanceAttestationReference",
        )
        union = [
            identity
            for phase in ("o2.1", "o2.2", "o2.3")
            for identity in pv.O2_SEQUENCING[phase]
        ]
        assert len(union) == 13
        assert len(set(union)) == 13
        assert set(pv.O2_SEQUENCING["o2.1"]) == set(pv.O21_ADMITTED_IDENTITIES)
        assert not (
            set(pv.O21_ADMITTED_IDENTITIES) & set(pv.O21_EXCLUDED_IDENTITIES)
        )

    def test_manifest_matches_frozen_locks(self) -> None:
        manifest = pv.load_admission_manifest(REPO_ROOT / pv.ADMISSION_PATH)
        pv.validate_admission(manifest)
        assert tuple(manifest["admitted"]) == pv.O21_ADMITTED_IDENTITIES
        assert {
            entry["identity"] for entry in manifest["excluded"]
        } == set(pv.O21_EXCLUDED_IDENTITIES)

    def test_every_excluded_identity_is_model_or_contract_known(self) -> None:
        """Every guard names a real identity (class or relationship)."""
        contract = KernelContract.load(REPO_ROOT / pv.ONTOLOGY_PATH)
        manifest = pv.load_admission_manifest(REPO_ROOT / pv.ADMISSION_PATH)
        kinds = {entry["identity"]: entry["kind"] for entry in manifest["excluded"]}
        for identity, kind in kinds.items():
            if kind == "class":
                assert identity in contract.classes, identity
            else:
                assert identity in contract.relationships, identity

    def _manifest(self) -> dict:
        return copy.deepcopy(
            pv.load_admission_manifest(REPO_ROOT / pv.ADMISSION_PATH)
        )

    def test_eighth_admission_fails(self) -> None:
        manifest = self._manifest()
        manifest["admitted"].append("VerificationCase")
        with pytest.raises(pv.ProjectionV1Error):
            pv.validate_admission(manifest)

    def test_missing_admission_fails(self) -> None:
        manifest = self._manifest()
        manifest["admitted"].remove("MethodPhase")
        with pytest.raises(pv.ProjectionV1Error):
            pv.validate_admission(manifest)

    def test_resequencing_fails(self) -> None:
        manifest = self._manifest()
        manifest["sequencing"]["o2.2"] = ["VerificationCase"]
        with pytest.raises(pv.ProjectionV1Error):
            pv.validate_admission(manifest)

    def test_excluded_guard_drift_fails(self) -> None:
        manifest = self._manifest()
        manifest["excluded"] = [
            entry
            for entry in manifest["excluded"]
            if entry["identity"] != "MethodEvaluationScope"
        ]
        with pytest.raises(pv.ProjectionV1Error):
            pv.validate_admission(manifest)

    def test_excluded_reason_required(self) -> None:
        manifest = self._manifest()
        for entry in manifest["excluded"]:
            if entry["identity"] == "DerivesFromNeed":
                entry["reason"] = " "
        with pytest.raises(pv.ProjectionV1Error):
            pv.validate_admission(manifest)

    def test_admitted_and_excluded_overlap_fails(self, monkeypatch) -> None:
        """The overlap guard fires when both locks are (adversarially) moved
        so an admitted identity also appears in the excluded guard set."""
        manifest = self._manifest()
        manifest["excluded"].append(
            {"identity": "MethodPhase", "kind": "class", "reason": "synthetic overlap"}
        )
        monkeypatch.setattr(
            pv, "O21_EXCLUDED_IDENTITIES", pv.O21_EXCLUDED_IDENTITIES + ("MethodPhase",)
        )
        with pytest.raises(pv.ProjectionV1Error, match="both admitted and excluded"):
            pv.validate_admission(manifest)

    def test_lock_disagreement_fails(self) -> None:
        """Swapping an admitted identity for an excluded one fails the lock."""
        manifest = self._manifest()
        manifest["admitted"][0] = "MethodEvaluationScope"
        with pytest.raises(pv.ProjectionV1Error):
            pv.validate_admission(manifest)


# ---------------------------------------------------------------------------
# 3. Negative scope (machine locks over real representations)
# ---------------------------------------------------------------------------


class TestNegativeScope:
    @pytest.mark.parametrize("identity", O21_NEGATIVE_IDENTITIES)
    def test_negative_identity_absent_from_rows(self, pair, identity) -> None:
        row_identities = {row["identity"] for row in pair["projection"]["concepts"]}
        assert identity not in row_identities
        for row in pair["projection"]["concepts"]:
            for member in row["structure"]["members"]:
                member_type = member.get("type")
                if member_type and member_type.get("kind") == "governed-class":
                    assert member_type["identity"] != identity

    def test_method_evaluation_scope_is_model_resident_but_excluded(self, pair) -> None:
        """Reviewed text equivalence is not a structural O2 admission.

        MethodEvaluationScope's documentation equivalence is reviewed
        (Layer-B governance) but its structural exclusions-with-rationale gap
        remains open; the identity is model-resident and discoverable yet
        must never appear in O2.1 output.
        """
        contract = KernelContract.load(REPO_ROOT / pv.ONTOLOGY_PATH)
        mapping = contract.mapping("MethodEvaluationScope")
        text = (REPO_ROOT / mapping.file).read_text(encoding="utf-8")
        assert pv.locate_declaration(text, mapping.declaration) is not None, (
            "MethodEvaluationScope must stay model-resident"
        )
        decisions = yaml.safe_load(
            (REPO_ROOT / "docs/method-conformance/o1/authority-review-decisions.yaml").read_text(
                encoding="utf-8"
            )
        )
        row = decisions["entries"]["MethodEvaluationScope"]
        assert row["semantic_text_equivalence"] == "reviewed-equivalent"
        assert row["evidence_state"] == "repository-evidenced"
        assert row["exact_fit_decision"].startswith("not exact structural fit")
        output = {row["identity"] for row in pair["projection"]["concepts"]}
        assert "MethodEvaluationScope" not in output

    def test_derives_from_need_is_model_resident_but_excluded(self, pair) -> None:
        """DerivesFromNeed keeps its K relationship semantics; no O2.1 class row."""
        contract = KernelContract.load(REPO_ROOT / pv.ONTOLOGY_PATH)
        mapping = contract.mapping("DerivesFromNeed")
        text = (REPO_ROOT / mapping.file).read_text(encoding="utf-8")
        assert pv.locate_declaration(text, mapping.declaration) is not None
        output = {row["identity"] for row in pair["projection"]["concepts"]}
        assert "DerivesFromNeed" not in output

    def test_blocked_and_rename_identities_are_discoverable_but_excluded(
        self, pair
    ) -> None:
        contract = KernelContract.load(REPO_ROOT / pv.ONTOLOGY_PATH)
        # rename-required and blocked identities keep implemented/declared
        # representation: representation existence does not override admission
        for identity in (
            "realizedBy",
            "specifiesFunction",
            "hasRelevantEvidenceContract",
        ):
            assert identity in contract.relationships
            assert contract.relationships[identity].get("sysml_mapping")
        # the retired identity keeps its authored contract row (retirement is
        # not absence) but has no traversal mapping
        assert "derivesNeedFromConcern" in contract.relationships
        assert not contract.relationships["derivesNeedFromConcern"].get(
            "sysml_mapping"
        )
        emitted = {row["identity"] for row in pair["projection"]["concepts"]}
        assert not emitted & {
            "realizedBy",
            "specifiesFunction",
            "hasRelevantEvidenceContract",
            "derivesNeedFromConcern",
        }

    def test_projection_v0_k_output_is_not_an_o21_violation(self, pair) -> None:
        """The K artifact contains K predicate rows by design; O2.1 output
        must not, and v1 never emits K rows (its emission path is the
        admission lock)."""
        k_identities = {
            "derivesRequirementFromNeed",
            "derivedRequirementsOfNeed",
            "DerivesFromNeed",
        }
        emitted = {row["identity"] for row in pair["projection"]["concepts"]}
        assert not emitted & k_identities
        assert not (set(pv.O21_ADMITTED_IDENTITIES) & k_identities)
        # the K identities appear only in the guard/sequencing constants
        assert k_identities <= (
            set(pv.O2_SEQUENCING["o2.3"]) | {"DerivesFromNeed"}
        )


# ---------------------------------------------------------------------------
# 4. Adversarial fixtures (A-I)
# ---------------------------------------------------------------------------


class TestAdversarial:
    def test_extra_model_vocabulary_does_not_expand_output(
        self, tmp_path, stubbed_gate
    ) -> None:
        """A: an additional governed class/declaration changes nothing."""

        def contract_mutator(contract: dict) -> None:
            contract["classes"]["ExtraVocabulary"] = {
                "definition": "Synthetic extra vocabulary (adversarial fixture).",
                "kernel": {
                    "file": CONFORMANCE_FILE,
                    "declaration": "item def ExtraVocabulary",
                },
            }

        def file_mutator(text: str) -> str:
            return text.replace(
                "  item def AcceptanceAttestationReference {",
                "  item def ExtraVocabulary {\n"
                "    doc /* Synthetic extra vocabulary. */\n"
                "    attribute note : String;\n"
                "  }\n\n"
                "  item def AcceptanceAttestationReference {",
            )

        root = _fixture_root(
            tmp_path,
            contract_mutator=contract_mutator,
            file_mutators={CONFORMANCE_FILE: file_mutator},
        )
        artifacts = pv.build_pair(root, source_revision="0" * 40)
        identities = [row["identity"] for row in artifacts["projection"]["concepts"]]
        assert identities == list(pv.O21_ADMITTED_IDENTITIES)

    def test_missing_admitted_declaration_fails_closed(
        self, tmp_path, stubbed_gate
    ) -> None:
        """B: one admitted declaration removed -> generation fails."""

        def file_mutator(text: str) -> str:
            return _remove_declaration(text, "item def TestedScopeDeclaration")

        root = _fixture_root(
            tmp_path, file_mutators={CONFORMANCE_FILE: file_mutator}
        )
        with pytest.raises(pv.ProjectionV1Error, match="TestedScopeDeclaration"):
            pv.build_pair(root, source_revision="0" * 40)

    def test_ambiguous_grounding_fails_closed(self, tmp_path, stubbed_gate) -> None:
        """C: duplicate declaration -> ambiguous grounding fails."""
        duplicate = (
            "\n  item def EvaluationScopeMembership {\n"
            "    doc /* Duplicate declaration (adversarial fixture). */\n"
            "    attribute scopeId : String;\n"
            "  }\n"
        )

        def file_mutator(text: str) -> str:
            return text + duplicate

        root = _fixture_root(
            tmp_path, file_mutators={CONFORMANCE_FILE: file_mutator}
        )
        with pytest.raises(pv.ProjectionV1Error, match="ambiguous grounding"):
            pv.build_pair(root, source_revision="0" * 40)

    def test_wrong_declaration_kind_fails_closed(self, tmp_path, stubbed_gate) -> None:
        """D/E: same name, wrong declared kind (model side) -> not resolvable."""

        def file_mutator(text: str) -> str:
            return text.replace(
                "item def AcceptanceAttestationReference",
                "part def AcceptanceAttestationReference",
            )

        root = _fixture_root(
            tmp_path, file_mutators={CONFORMANCE_FILE: file_mutator}
        )
        with pytest.raises(pv.ProjectionV1Error, match="AcceptanceAttestationReference"):
            pv.build_pair(root, source_revision="0" * 40)

    def test_contract_kind_drift_fails_closed(self, tmp_path, stubbed_gate) -> None:
        """E: contract expects enum, model declares item -> no name recovery."""

        def contract_mutator(contract: dict) -> None:
            contract["classes"]["EvaluationSourceKind"]["kernel"][
                "declaration"
            ] = "enum def EvaluationSourceKind"
            # and force an unsupported-kind path via a wrong kind:
            contract["classes"]["MethodContractObligation"]["kernel"][
                "declaration"
            ] = "enum def MethodContractObligation"

        root = _fixture_root(tmp_path, contract_mutator=contract_mutator)
        with pytest.raises(pv.ProjectionV1Error, match="MethodContractObligation"):
            pv.build_pair(root, source_revision="0" * 40)

    def test_no_documentation_fails_closed(self, tmp_path, stubbed_gate) -> None:
        """F: correct metaclass, missing documentation -> fail closed."""

        def file_mutator(text: str) -> str:
            located = pv.locate_declaration(text, "item def TestedScopeDeclaration")
            assert located is not None
            _, brace_start, block = located
            stripped = re.sub(r"doc /\*.*?\*/\s*", "", block, flags=re.DOTALL)
            return text[:brace_start] + stripped + text[brace_start + len(block):]

        root = _fixture_root(
            tmp_path, file_mutators={CONFORMANCE_FILE: file_mutator}
        )
        with pytest.raises(pv.ProjectionV1Error, match="documentation"):
            pv.build_pair(root, source_revision="0" * 40)

    def test_unresolved_member_typing_fails_closed(self, tmp_path, stubbed_gate) -> None:
        """F: an attribute typed by an unknown, non-governed type fails."""

        def file_mutator(text: str) -> str:
            return text.replace(
                "    attribute executionHead : String;",
                "    attribute executionHead : UnknownType;",
            )

        root = _fixture_root(
            tmp_path, file_mutators={CONFORMANCE_FILE: file_mutator}
        )
        with pytest.raises(pv.ProjectionV1Error, match="UnknownType"):
            pv.build_pair(root, source_revision="0" * 40)

    def test_unsupported_member_form_fails_closed(self, tmp_path, stubbed_gate) -> None:
        """F: an unmodeled member form fails closed rather than being dropped."""

        def file_mutator(text: str) -> str:
            return text.replace(
                "    attribute executionHead : String;",
                "    ref extraHandle : String;\n"
                "    attribute executionHead : String;",
            )

        root = _fixture_root(
            tmp_path, file_mutators={CONFORMANCE_FILE: file_mutator}
        )
        with pytest.raises(pv.ProjectionV1Error, match="unsupported member form"):
            pv.build_pair(root, source_revision="0" * 40)

    def test_o1_data_cannot_manufacture_a_row(self, tmp_path, stubbed_gate) -> None:
        """G: decoy O1 data cannot manufacture a semantic row.

        With an admitted declaration deleted AND decoy O1 inventory data
        present, generation still fails closed: the O1 migration inventory is
        never read and supplies no semantic field.
        """

        def file_mutator(text: str) -> str:
            return _remove_declaration(text, "item def TestedScopeDeclaration")

        root = _fixture_root(
            tmp_path,
            file_mutators={CONFORMANCE_FILE: file_mutator},
            with_decoy_o1=True,
        )
        with pytest.raises(pv.ProjectionV1Error, match="TestedScopeDeclaration"):
            pv.build_pair(root, source_revision="0" * 40)

    def test_generation_without_any_o1_directory(self, tmp_path, stubbed_gate) -> None:
        """G: a checkout without O1 artifacts generates identically."""
        root = _fixture_root(tmp_path)
        assert not (root / "docs/method-conformance/o1").exists()
        artifacts = pv.build_pair(root, source_revision="0" * 40)
        identities = [row["identity"] for row in artifacts["projection"]["concepts"]]
        assert identities == list(pv.O21_ADMITTED_IDENTITIES)

    def test_representation_existence_does_not_override_admission(
        self, tmp_path, stubbed_gate
    ) -> None:
        """I: a fully representable but non-admitted identity is not emitted."""
        # MethodEvaluationScope is fully model-resident; even with a supported
        # kind it must not be emitted (guarded by the admission lock, checked
        # in TestNegativeScope). Here: a synthetic supported-kind class that
        # is NOT admitted is likewise absent.
        root = _fixture_root(tmp_path)
        artifacts = pv.build_pair(root, source_revision="0" * 40)
        emitted = {row["identity"] for row in artifacts["projection"]["concepts"]}
        assert emitted == set(pv.O21_ADMITTED_IDENTITIES)

    def test_lock_tamper_is_rejected_by_double_lock(self, tmp_path, stubbed_gate) -> None:
        """Editing only the code lock (not the manifest) fails closed."""
        root = _fixture_root(tmp_path)
        original = pv.O21_ADMITTED_IDENTITIES
        try:
            pv.O21_ADMITTED_IDENTITIES = original + ("VerificationCase",)
            with pytest.raises(pv.ProjectionV1Error):
                pv.build_pair(root, source_revision="0" * 40)
        finally:
            pv.O21_ADMITTED_IDENTITIES = original


# ---------------------------------------------------------------------------
# 5. Projection v0 compatibility
# ---------------------------------------------------------------------------


class TestProjectionV0Compatibility:
    def test_v0_module_untouched_and_importable_after_v1(self) -> None:
        from de4sdv.semantic import projection as v0
        from de4sdv.semantic import projection_v1 as v1_module

        assert v0.PROJECTION_SCHEMA == "de4sdv.semantic-projection.v0"
        assert v0.PROFILE_SCHEMA == "de4sdv.api-representation-profile.v0"
        assert v1_module.PROJECTION_V1_SCHEMA == "de4sdv.semantic-projection.v1"
        # v0 module state is unchanged by importing the additive v1 module
        assert v0.PROJECTION_SCHEMA == "de4sdv.semantic-projection.v0"
        assert v0.PROFILE_IDENTITY.startswith("de4sdv.api-representation-profile.v0#")

    def test_v1_does_not_import_v0(self) -> None:
        source = (REPO_ROOT / "de4sdv/semantic/projection_v1.py").read_text(
            encoding="utf-8"
        )
        assert "from .projection import" not in source
        assert "import projection\n" not in source

    def test_v0_builders_unchanged_via_fixture(self) -> None:
        """The K fixture projection still builds with its pinned semantics."""
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from de4sdv.semantic.kernel_binding_index import KernelBindingIndex
        from de4sdv.semantic.projection import (
            RevisionIdentity,
            build_projection,
        )
        from test_derivation_connection_traversal import (  # noqa: E402
            _binding_index,
            _contract,
            _default_binding_entries,
            _elements,
        )

        by_id = {item["@id"]: item for item in _elements()}
        projection = build_projection(
            _contract(),
            _binding_index(list(_default_binding_entries())),
            RevisionIdentity("0" * 40, "proj-0001", "commit-0001"),
            by_id,
            repository_root=REPO_ROOT,
        )
        assert projection["schema"] == "de4sdv.semantic-projection.v0"
        assert projection["predicate"]["identity"] == "derivesRequirementFromNeed"
        assert projection["predicate"]["support_state"] == "vocabulary-only"

    def test_v0_k_consumers_still_pass(self) -> None:
        """The full v0/K regression suites are run by the repository gate;
        this test pins the entry points remain importable and green here."""
        from de4sdv.semantic.projection import (
            assert_profile_compatible,
            build_representation_profile,
        )

        assert callable(assert_profile_compatible)
        assert callable(build_representation_profile)


# ---------------------------------------------------------------------------
# 6. Runtime independence and committed-artifact consistency
# ---------------------------------------------------------------------------


class TestRuntimeIndependence:
    def test_no_runtime_module_touches_v1(self) -> None:
        """No runtime semantic module imports projection_v1 or reads the
        generated artifacts (O3 owns any activation)."""
        runtime_modules = sorted(
            path
            for path in (REPO_ROOT / "de4sdv").rglob("*.py")
            if path.name
            not in {
                "projection_v1.py",
                "authority_inventory.py",
                "generate_semantic_projection_v1.py",
            }
        )
        for path in runtime_modules:
            text = path.read_text(encoding="utf-8")
            assert "projection_v1" not in text, f"{path}: imports v1 machinery"
            assert "semantic-projection-v1" not in text, f"{path}: reads v1 artifacts"

    def test_generator_is_not_importable_by_runtime_consumers(self) -> None:
        """The v1 module is build-time only; the semantic runtime package
        entry points do not reference it."""
        for module in ("query", "traversal", "runtime", "mcp_server", "impact"):
            text = (REPO_ROOT / f"de4sdv/semantic/{module}.py").read_text(
                encoding="utf-8"
            )
            assert "projection_v1" not in text


# ---------------------------------------------------------------------------
# STAGE B (O2.1 artifact publication) — deferred by the squash-safe
# delivery sequence: the committed-artifact consistency tests and the
# check_repo gate-registration test activate in Stage B, after the Stage A
# squash-merge provides the permanent main source_revision. Their intent is
# preserved and they are re-added verbatim in the Stage B PR (extracted
# copy: o2-stage-b-deferred-tests.py; branch history at 866a6f5).
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _row(pair: dict, identity: str) -> dict:
    for row in pair["projection"]["concepts"]:
        if row["identity"] == identity:
            return row
    raise AssertionError(f"missing row {identity}")


def _type_label(member_type: dict) -> str:
    return member_type.get("identity") or member_type.get("name")


def _all_keys(value: object):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _all_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _all_keys(item)