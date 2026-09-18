"""O2.2 — Semantic Projection v1.1 / API Representation Profile v1.1 tests.

Covers the O2.2 additive generation stage (Stage A: implementation
foundation; the canonical v1.1 artifacts and the repository gate
registration are published in Stage B — see the design record):

1.  **positive scope**: exactly the three settled c2/c3 identities are
    generated (``VerificationCase``, ``hasSubject``, ``verifiedBy``), each
    exactly once, with the reviewed representation contract (domain, range,
    witness strategy, membership witnesses, semantic strength) and the
    governed model anchors derived from the ACTUAL production model
    declarations — not only synthetic fixtures;
2.  **extends discipline**: the extension pins the immutable O2.1 baseline
    by path, schema, source revision, and artifact digest, and never
    re-emits or re-binds the O2.1 seven;
3.  **machine-locked admission**: the admission manifest and the frozen O2
    sequencing agree exactly (three admitted; 13-identity sequencing union;
    cumulative O2.1+O2.2 surface exactly ten); manifest drift fails closed;
4.  **negative scope**: the guarded identities (the O2.1 seven, the O2.3
    set, MethodEvaluationScope, DerivesFromNeed, the retired/blocked/
    rename-required set) never appear as O2.2 rows even though their
    representations are model-resident and discoverable;
5.  **adversarial fixtures**: extra model vocabulary does not expand the
    output; a missing admitted declaration, ambiguous grounding, wrong
    structural identity, wrong metaclass shape, missing required grounding,
    and contract drift all fail closed; the generator does not read O1
    migration artifacts (a checkout without them generates identically, and
    decoy O1 data cannot manufacture a row);
6.  **O2.1 preservation**: the v1 baseline artifacts still pass their own
    repository gate; Projection v0 is byte-unchanged;
7.  **runtime independence**: no runtime module imports the v1.1 machinery
    or reads the v1.1 artifacts; support states come from a closed
    vocabulary with no promotion input.

Stage B (artifact publication) activates the committed-artifact consistency
tests and the ``check_repo`` gate-registration test: the canonical v1.1
artifacts now exist, parse, byte-match deterministic regeneration, and the
repository gate invokes the v1.1 ``--check`` fail-closed. The artifacts bind
the permanent Stage A revision the #253 squash-merge produced — not any
feature-branch commit.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic import projection_o22 as po22
from de4sdv.semantic import projection_v1 as pv

REPO_ROOT = Path(__file__).resolve().parents[1]

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
)

#: Identities that must never appear as O2.2 rows (sampled across every
#: guarded category; the complete guard set is machine-derived).
O22_NEGATIVE_IDENTITIES = (
    "MethodEvaluationScope",
    "DerivesFromNeed",
    "derivesRequirementFromNeed",
    "derivedRequirementsOfNeed",
    "hasRelevantArchitecture",
    "derivesNeedFromConcern",
    "realizedBy",
    "specifiesFunction",
    "hasRelevantEvidenceContract",
    "EvidenceContract",
    "ArchitectureElement",
    "allocatedTo",
    "deployedTo",
)

#: The O2.2 bound model inputs (derived mechanically in the module; pinned
#: here for fixture construction and reviewability).
_METHOD_CONTEXT_FILE = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml"
_PRODUCT_LINE_FILE = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml"
_MODEL_FILES = (
    _METHOD_CONTEXT_FILE,
    _PRODUCT_LINE_FILE,
    po22.VERIFICATION_MODEL_FILE,
)

#: Reviewed witness state of the current governed model (locked in the tests,
#: derived by the generator): the six declared verification usages and the
#: three objective verify targets.
EXPECTED_USAGE_SHORT_NAMES = (
    "VC-AEBS-009D-01",
    "VC-AEBS-009D-02",
    "VC-AEBS-009D-03",
    "VC-AEBS-009D-04",
    "VC-AEBS-009D-05",
    "VC-AEBS-009D-06",
)
EXPECTED_VERIFY_TARGETS = (
    "evidenceContractClosedOverrideScenario",
    "evidenceContractOverrideFreshnessReplay",
    "evidenceContractIndependentVerdict",
)


@pytest.fixture(scope="module")
def pair() -> dict:
    """The real extension artifacts, generated against the committed checkout."""
    return po22.build_pair_o22(REPO_ROOT)


@pytest.fixture()
def stubbed_gate(monkeypatch):
    """Fixture repos are not Git checkouts: stub the containment gate.

    The real gate is exercised against the committed repository by the
    module-level ``pair`` fixture; synthetic fixtures test derivation
    fail-closed behavior.
    """
    monkeypatch.setattr(
        po22, "verify_source_revision_contains_inputs", lambda *a, **k: None
    )


def _declaration_block(text: str, declaration: str) -> tuple[int, int]:
    """(start, end) of one braced declaration statement in ``text``."""
    kind, _, name = declaration.partition(" def ")
    import re

    pattern = re.compile(
        r"(?m)^[ \t]*(?:(?:public|private|protected)\s+)?(?:abstract\s+)?"
        + re.escape(kind.strip()).replace(r"\ ", r"\s+")
        + r"\s+def\s+"
        + re.escape(name.strip())
        + r"\b"
    )
    match = pattern.search(text)
    assert match is not None, declaration
    brace = text.find("{", match.end())
    assert brace != -1, declaration
    close = po22._matching_brace(text, brace)
    return match.start(), close + 1


def _remove_declaration(text: str, declaration: str) -> str:
    start, end = _declaration_block(text, declaration)
    return text[:start] + text[end:]


def _row_blob(pair: dict) -> str:
    """Canonical serialization of the emitted rows only (concepts+predicates)."""
    rows = list(pair["projection"]["concepts"]) + list(pair["projection"]["predicates"])
    return po22.canonical_json({"rows": rows})


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
    contract_path = REPO_ROOT / po22.ONTOLOGY_PATH
    files = [
        po22.ONTOLOGY_PATH,
        po22.ADMISSION_O22_PATH,
        po22.BASELINE_PROJECTION_V1_PATH,
        po22.BASELINE_PROFILE_V1_PATH,
        *po22.BOUND_INPUT_PROGRAM_PATHS_O22,
        *_MODEL_FILES,
    ]
    for rel in files:
        destination = root / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((REPO_ROOT / rel).read_bytes())
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    if contract_mutator is not None:
        contract_mutator(contract)
    (root / po22.ONTOLOGY_PATH).write_text(
        yaml.safe_dump(contract, sort_keys=False), encoding="utf-8"
    )
    for rel, mutator in (file_mutators or {}).items():
        target = root / rel
        target.write_text(mutator(target.read_text(encoding="utf-8")), encoding="utf-8")
    if manifest_mutator is not None:
        manifest = yaml.safe_load(
            (REPO_ROOT / po22.ADMISSION_O22_PATH).read_text(encoding="utf-8")
        )
        manifest_mutator(manifest)
        (root / po22.ADMISSION_O22_PATH).write_text(
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
                        for identity in po22.O22_ADMITTED_IDENTITIES
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
    def test_exactly_three_identities_in_order_once_each(self, pair) -> None:
        rows = list(pair["projection"]["concepts"]) + list(
            pair["projection"]["predicates"]
        )
        identities = [row["identity"] for row in rows]
        assert tuple(identities) == po22.O22_ADMITTED_IDENTITIES

    def test_verification_case_row(self, pair) -> None:
        row = pair["projection"]["concepts"][0]
        assert row["identity"] == "VerificationCase"
        assert row["semantic_kind"] == "verification-case"
        assert row["support_state"] == po22.SUPPORT_STATE_VOCABULARY_ONLY
        construct = row["construct"]
        assert construct["kind"] == "native"
        grounding = construct["native_grounding"]
        assert "VerificationCase" in grounding["identity"]
        assert "pinned standard library" in grounding["identity"]
        # Representation mechanics are NOT in the projection row: no library
        # role ids, no implied-edge mechanisms, no API metaclasses, no
        # evidence/export mechanics.
        blob = po22.canonical_json({"row": row})
        for banned in (
            "VerificationCases::",
            "implied",
            "Subclassification",
            "Subsetting",
            "VerificationCaseDefinition",
            "VerificationCaseUsage",
            "exporter",
            "read-back",
        ):
            assert banned not in blob, banned

    def test_verification_case_mechanics_in_profile(self, pair) -> None:
        entry = pair["profile"]["profiles"][0]
        assert entry["for_identity"] == "VerificationCase"
        mechanics = entry["library_grounding_mechanics"]
        assert mechanics["definition_role"]["library_identity"] == (
            "VerificationCases::VerificationCase"
        )
        assert mechanics["definition_role"]["mechanism"] == "implied Subclassification"
        assert mechanics["usage_role"]["library_identity"] == (
            "VerificationCases::verificationCases"
        )
        assert mechanics["usage_role"]["mechanism"] == "implied Subsetting"
        assert mechanics["definition_role"]["provenance"] == "implied"
        assert "controlled standard-library proof" in mechanics["library_proof_step"]
        assert "run-pinned" in mechanics["anchor_policy"]
        assert entry["api_metaclasses"] == [
            "VerificationCaseDefinition",
            "VerificationCaseUsage",
        ]

    def test_verification_case_model_evidence(self, pair) -> None:
        row = pair["projection"]["concepts"][0]
        definition = row["model_evidence"]["definition"]
        assert definition["source_file"] == po22.VERIFICATION_MODEL_FILE
        assert definition["declared_short_name"] == "VC-AEBS-009D-DE"
        assert (
            tuple(definition["objective_verify_targets"]) == EXPECTED_VERIFY_TARGETS
        )
        usages = row["model_evidence"]["usages"]
        assert tuple(usage["declared_short_name"] for usage in usages) == (
            EXPECTED_USAGE_SHORT_NAMES
        )
        for usage in usages:
            assert usage["specializes"] == "ConsciousOverrideVerification"
            assert "api_metaclass" not in usage

    def test_has_subject_row(self, pair) -> None:
        row = pair["projection"]["predicates"][0]
        assert row["identity"] == "hasSubject"
        assert row["semantic_kind"] == "relationship"
        assert row["support_state"] == po22.SUPPORT_STATE_VOCABULARY_ONLY
        relation = row["relation"]
        assert set(relation) == {
            "domain",
            "range",
            "canonical_direction",
            "inverse_navigation",
            "semantic_strength",
            "native_grounding",
            "scope_restrictions",
        }
        assert relation["domain"]["ontology_class"] == "Requirement"
        assert relation["domain"]["lineage"]["declaration"] == (
            "requirement def RequirementCandidate"
        )
        assert relation["domain"]["lineage"]["file"] == _METHOD_CONTEXT_FILE
        assert relation["range"]["ontology_class"] == "MemberProduct"
        assert relation["range"]["lineage"]["declaration"] == (
            "part def ProductLineMemberProduct"
        )
        assert relation["range"]["lineage"]["file"] == _PRODUCT_LINE_FILE
        assert relation["canonical_direction"] == "Requirement -> MemberProduct"
        assert relation["semantic_strength"] == "native-reference"
        assert relation["native_grounding"]["native_construct"] == "SubjectMembership"
        axes = [entry["axis"] for entry in relation["scope_restrictions"]]
        assert axes == ["source", "target"]
        assert "not a query convenience" in relation["scope_restrictions"][0]["meaning"]

    def test_has_subject_mechanics_in_profile(self, pair) -> None:
        entry = {e["for_identity"]: e for e in pair["profile"]["profiles"]}["hasSubject"]
        mechanics = entry["serializer_mechanics"]
        assert mechanics["strategy"] == "subject-membership"
        assert mechanics["membership_types"] == ["SubjectMembership"]
        assert mechanics["member_property"] == "memberElement"
        assert mechanics["owner_types"] == ["RequirementUsage"]
        assert entry["runtime_mapping_state"] == (
            "existing-not-authority"
        )
        forms = entry["witness_forms"]
        assert any("memberElement" in form for form in forms)
        assert any("ReferenceUsage or PartUsage" in form for form in forms)

    def test_verified_by_row(self, pair) -> None:
        row = pair["projection"]["predicates"][1]
        assert row["identity"] == "verifiedBy"
        assert row["support_state"] == po22.SUPPORT_STATE_VOCABULARY_ONLY
        relation = row["relation"]
        assert relation["domain"]["ontology_class"] == "Requirement"
        assert relation["range"]["ontology_class"] == "VerificationCase"
        assert relation["range"]["row_ref"] == "VerificationCase"
        assert relation["canonical_direction"] == "Requirement -> VerificationCase"
        assert relation["semantic_strength"] == "native-verification"
        assert relation["native_grounding"]["native_construct"] == (
            "RequirementVerificationMembership"
        )
        assert "coverage relation only" in relation["native_grounding"]["note"]
        axes = [entry["axis"] for entry in relation["scope_restrictions"]]
        assert axes == ["source"]

    def test_verified_by_mechanics_in_profile(self, pair) -> None:
        entry = {e["for_identity"]: e for e in pair["profile"]["profiles"]}["verifiedBy"]
        mechanics = entry["serializer_mechanics"]
        assert mechanics["strategy"] == "verification-membership"
        assert mechanics["membership_types"] == ["RequirementVerificationMembership"]
        assert mechanics["reference_property"] == "verifiedRequirement"
        assert mechanics["direction"] == "reverse"
        assert set(mechanics["element_types"]) == {
            "VerificationCaseUsage",
            "VerificationCaseDefinition",
        }
        assert set(mechanics["owner_membership_types"]) == {
            "FeatureMembership",
            "OwningMembership",
            "ObjectiveMembership",
            "RequirementVerificationMembership",
        }
        assert entry["runtime_mapping_state"] == "existing-not-authority"
        forms = entry["witness_forms"]
        assert any("ReferenceSubsetting" in form for form in forms)
        assert any("ownership chain" in form for form in forms)
        assert any("direction extraction is reverse" in form for form in forms)

    def test_scope_block_is_machine_locked(self, pair) -> None:
        scope = pair["projection"]["scope"]
        assert tuple(scope["admitted"]) == po22.O22_ADMITTED_IDENTITIES
        cumulative = scope["cumulative_surface"]
        assert cumulative["total"] == 10
        assert tuple(cumulative["o2_1"]) == pv.O21_ADMITTED_IDENTITIES
        assert tuple(cumulative["o2_2"]) == po22.O22_ADMITTED_IDENTITIES
        guarded = {entry["identity"] for entry in scope["guarded"]}
        assert guarded == set(po22.O22_GUARDED_IDENTITIES)
        assert not (guarded & set(po22.O22_ADMITTED_IDENTITIES))

    def test_projection_contract_is_top_level(self, pair) -> None:
        projection = pair["projection"]
        assert "projection_contract" in projection
        contract = projection["projection_contract"]
        assert "verification execution or results" in contract["does_not_assert"]
        assert "identity_claim_boundaries" in contract
        rows = list(projection["concepts"]) + list(projection["predicates"])
        for row in rows:
            assert "claim_boundary" not in row
            assert "projection_contract" not in row

    def test_claim_boundaries_are_schema_level_reviewed_metadata(self, pair) -> None:
        boundaries = pair["projection"]["projection_contract"][
            "identity_claim_boundaries"
        ]
        assert set(boundaries) == {"hasSubject", "verifiedBy"}
        hs = " ".join(boundaries["hasSubject"]["does_not_assert"])
        vb = " ".join(boundaries["verifiedBy"]["does_not_assert"])
        for law in (
            "RequirementVerificationMembership",
            "memberProduct",
            "same-named",
            "allocation",
            "instantiation",
            "verification success",
        ):
            assert law in hs, law
        for law in (
            "generic Dependency",
            "SubjectMembership",
            "VerificationMethod metadata",
            "execution records",
            "evaluation records",
            "name-only correspondence",
            "certification",
        ):
            assert law in vb, law
        # The laws are schema-level: no row serializes them as its own fields.
        blob = _row_blob(pair)
        for marker in ("does_not_assert", "named_non_witnesses", "semantic_exclusions"):
            assert marker not in blob, marker

    def test_claim_boundary_registry_is_machine_locked(self, pair) -> None:
        boundaries = pair["projection"]["projection_contract"][
            "identity_claim_boundaries"
        ]
        # Every reviewed registry entry must be covered by the serialized
        # schema-level claim boundaries (the registry is the reviewed source;
        # the artifact must not silently drop a law).
        coverage = {
            "hasSubject": (
                "requirementverificationmembership",
                "generic",  # generic untyped PartUsage
                "memberproduct",  # parts merely named memberProduct
                "same-named",
                "selection",  # PLE selection or configuration membership
                "allocation",
                "realization",
                "instantiation",
                "satisfaction",
                "verification success",
            ),
            "verifiedBy": (
                "generic",  # generic Dependency
                "subjectmembership",
                "verificationmethod",
                "retained",  # retained execution records
                "evaluation",
                "name-only",
                "verification-looking",
            ),
        }
        for identity, tokens in coverage.items():
            text = po22.canonical_json(boundaries[identity]).lower()
            for token in tokens:
                assert token in text, (identity, token)
        # The reviewed registry itself stays locked (the serialized boundary
        # must not drift from the reviewed laws it covers).
        assert po22._O22_NEGATIVE_WITNESSES["hasSubject"][0] == (
            "RequirementVerificationMembership"
        )
        assert "a part merely named `memberProduct`" in (
            po22._O22_NEGATIVE_WITNESSES["hasSubject"]
        )
        assert "generic Dependency" in po22._O22_NEGATIVE_WITNESSES["verifiedBy"]
        assert "VerificationMethod metadata" in (
            po22._O22_NEGATIVE_WITNESSES["verifiedBy"]
        )

    def test_projection_rows_contain_no_representation_mechanics(self, pair) -> None:
        blob = _row_blob(pair)
        banned_keys = (
            "member_property",
            "reference_property",
            "owner_types",
            "owner_membership_types",
            "element_types",
            "strategy",
            "direction",
        )
        for key in banned_keys:
            assert f'"{key}"' not in blob, key
        banned_terms = (
            "ReferenceSubsetting",
            "memberElement",
            "owningRelatedElement",
            "ownership chain",
            "shadow",
            "serializer",
            "Subclassification",
            "Subsetting",
            "metaclass",
            "exporter",
            "read-back",
            "implied",
        )
        for term in banned_terms:
            assert term not in blob, term

    def test_profile_entries_echo_and_separation(self, pair) -> None:
        profiles = pair["profile"]["profiles"]
        assert [entry["for_identity"] for entry in profiles] == list(
            po22.O22_ADMITTED_IDENTITIES
        )
        by_identity = {entry["for_identity"]: entry for entry in profiles}
        vc = pair["projection"]["concepts"][0]
        assert by_identity["VerificationCase"]["representation_class"] == (
            "native-verification-construct"
        )
        assert by_identity["VerificationCase"]["semantic_contract_echo"] == {
            "native_grounding": vc["construct"]["native_grounding"]["identity"]
        }
        for identity, row in (
            ("hasSubject", pair["projection"]["predicates"][0]),
            ("verifiedBy", pair["projection"]["predicates"][1]),
        ):
            relation = row["relation"]
            assert by_identity[identity]["semantic_contract_echo"] == {
                "domain": relation["domain"]["ontology_class"],
                "range": relation["range"]["ontology_class"],
                "canonical_direction": relation["canonical_direction"],
                "semantic_strength": relation["semantic_strength"],
                "scope_restrictions": [
                    item["restriction"] for item in relation["scope_restrictions"]
                ],
            }
            assert by_identity[identity]["serializer_mechanics"]["strategy"]
            assert by_identity[identity]["representation_class"] == (
                f"{by_identity[identity]['serializer_mechanics']['strategy']}"
                "-relationship"
            )

    def test_extends_pins_the_correct_baseline_per_artifact(self, pair) -> None:
        projection_pin = pair["projection"]["extends"]
        profile_pin = pair["profile"]["extends"]
        # BLOCKER A: each extension independently extends its own baseline.
        assert projection_pin["artifact"] == po22.BASELINE_PROJECTION_V1_PATH
        assert projection_pin["schema"] == pv.PROJECTION_V1_SCHEMA
        assert profile_pin["artifact"] == po22.BASELINE_PROFILE_V1_PATH
        assert profile_pin["schema"] == pv.PROFILE_V1_SCHEMA
        assert projection_pin != profile_pin
        for pin, path in (
            (projection_pin, po22.BASELINE_PROJECTION_V1_PATH),
            (profile_pin, po22.BASELINE_PROFILE_V1_PATH),
        ):
            baseline = json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))
            assert pin["source_revision"] == baseline["binding"]["source_revision"]
            import hashlib

            expected = "sha256:" + hashlib.sha256(
                (REPO_ROOT / path).read_bytes()
            ).hexdigest()
            assert pin["artifact_digest"] == expected

    def test_shared_baseline_revision_is_verified_not_assumed(self, pair) -> None:
        # The O2.1 projection/profile pair currently share one source
        # revision; the extension records each pin independently and this
        # test verifies the current fact rather than the module assuming it.
        projection_pin = pair["projection"]["extends"]
        profile_pin = pair["profile"]["extends"]
        assert projection_pin["source_revision"] == profile_pin["source_revision"]

    def test_both_baselines_are_bound_inputs(self, pair) -> None:
        bound = pair["projection"]["binding"]["bound_inputs"]
        assert po22.BASELINE_PROJECTION_V1_PATH in bound
        assert po22.BASELINE_PROFILE_V1_PATH in bound
        assert pair["projection"]["binding"]["baseline_projection"]["path"] == (
            po22.BASELINE_PROJECTION_V1_PATH
        )
        assert pair["projection"]["binding"]["baseline_profile"]["path"] == (
            po22.BASELINE_PROFILE_V1_PATH
        )

    def test_binding_shape(self, pair) -> None:
        binding = pair["projection"]["binding"]
        assert binding["api_binding"]["status"] == "unclaimed"
        assert binding["artifact_commit"] is None
        assert po22.PROJECTION_V11_JSON_PATH not in binding["bound_inputs"]
        program = set(binding["generation_software"]["program_inputs"])
        assert program == set(po22.BOUND_INPUT_PROGRAM_PATHS_O22)

    def test_support_state_is_vocabulary_only_for_all_rows(self, pair) -> None:
        rows = list(pair["projection"]["concepts"]) + list(
            pair["projection"]["predicates"]
        )
        for row in rows:
            assert row["support_state"] == "vocabulary-only", row["identity"]
        assert po22.SUPPORT_STATE_VOCABULARY_ONLY == "vocabulary-only"
        # No other support vocabulary and no promotion path exists.
        assert not hasattr(po22, "O22_SUPPORT_STATES")
        assert not hasattr(po22, "SUPPORT_STATE_IMPLEMENTED_MAPPING")
        import inspect

        signature = inspect.signature(po22.build_pair_o22)
        assert "support" not in signature.parameters
        assert "promote" not in signature.parameters
        # The runtime-mapping fact is non-support metadata, only in the
        # representation profile.
        predicate_rows = pair["projection"]["predicates"]
        assert po22.canonical_json({"r": predicate_rows}).count(
            "existing-not-authority"
        ) == 0
        profile_entries = {e["for_identity"]: e for e in pair["profile"]["profiles"]}
        assert profile_entries["hasSubject"]["runtime_mapping_state"] == (
            "existing-not-authority"
        )
        assert profile_entries["verifiedBy"]["runtime_mapping_state"] == (
            "existing-not-authority"
        )

    def test_deterministic_serialization(self, pair) -> None:
        rebuilt = po22.build_pair_o22(
            REPO_ROOT,
            source_revision=pair["projection"]["binding"]["source_revision"],
        )
        assert po22.canonical_json(rebuilt["projection"]) == po22.canonical_json(
            pair["projection"]
        )
        assert po22.canonical_json(rebuilt["profile"]) == po22.canonical_json(
            pair["profile"]
        )


# ---------------------------------------------------------------------------
# 2. Admission machine locks
# ---------------------------------------------------------------------------


class TestAdmissionLock:
    def test_manifest_matches_frozen_locks(self) -> None:
        manifest = po22.load_admission_manifest_o22(
            REPO_ROOT / po22.ADMISSION_O22_PATH
        )
        po22.validate_admission_o22(manifest)
        assert tuple(manifest["admitted"]) == po22.O22_ADMITTED_IDENTITIES
        assert {entry["identity"] for entry in manifest["guarded"]} == set(
            po22.O22_GUARDED_IDENTITIES
        )

    def test_cumulative_surface_is_ten_distinct(self) -> None:
        surface = po22.O22_CUMULATIVE_SURFACE
        assert len(surface) == 10
        assert len(set(surface)) == 10
        assert set(pv.O21_ADMITTED_IDENTITIES) | set(po22.O22_ADMITTED_IDENTITIES) == set(
            surface
        )

    def test_eighth_identity_admission_fails(self, tmp_path, stubbed_gate) -> None:
        def mutate(manifest):
            manifest["admitted"].append("derivesRequirementFromNeed")

        root = _fixture_root(tmp_path, manifest_mutator=mutate)
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)

    def test_missing_admitted_identity_fails(self, tmp_path, stubbed_gate) -> None:
        def mutate(manifest):
            manifest["admitted"] = ["VerificationCase", "hasSubject"]

        root = _fixture_root(tmp_path, manifest_mutator=mutate)
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)

    def test_guarded_set_drift_fails(self, tmp_path, stubbed_gate) -> None:
        def mutate(manifest):
            manifest["guarded"].pop()

        root = _fixture_root(tmp_path, manifest_mutator=mutate)
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)

    def test_overlap_admitted_and_guarded_fails(self, tmp_path, stubbed_gate) -> None:
        def mutate(manifest):
            manifest["guarded"].append(
                {"identity": "VerificationCase", "kind": "class", "reason": "decoy"}
            )
            manifest["guarded"] = [
                entry
                for entry in manifest["guarded"]
                if not (entry["identity"] == "MethodPhase")
            ]

        root = _fixture_root(tmp_path, manifest_mutator=mutate)
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)

    def test_sequencing_drift_fails(self, tmp_path, stubbed_gate) -> None:
        def mutate(manifest):
            manifest["sequencing"]["o2.3"] = ["hasRelevantArchitecture"]

        root = _fixture_root(tmp_path, manifest_mutator=mutate)
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)


# ---------------------------------------------------------------------------
# 3. Negative scope (guarded identities and re-emission locks)
# ---------------------------------------------------------------------------


class TestNegativeScope:
    def test_guarded_identities_never_appear(self, pair) -> None:
        rows = list(pair["projection"]["concepts"]) + list(
            pair["projection"]["predicates"]
        )
        emitted = {row["identity"] for row in rows}
        for identity in O22_NEGATIVE_IDENTITIES:
            assert identity not in emitted
        assert not (emitted & set(pv.O21_ADMITTED_IDENTITIES))
        assert not (emitted & set(po22.O22_GUARDED_IDENTITIES))

    def test_o21_baseline_is_not_re_emitted(self, pair) -> None:
        scope = pair["projection"]["scope"]
        cumulative = scope["cumulative_surface"]
        assert set(cumulative["o2_1"]) & set(cumulative["o2_2"]) == set()
        guarded = {entry["identity"]: entry for entry in scope["guarded"]}
        for identity in pv.O21_ADMITTED_IDENTITIES:
            assert "immutable O2.1 baseline" in guarded[identity]["reason"]

    def test_method_evaluation_scope_model_resident_but_absent(self, pair) -> None:
        # MethodEvaluationScope is model-resident (declared in the method
        # conformance file and referenced by the O2.2 witness file) yet must
        # never appear as an O2.2 row: text equivalence is not structural
        # admission. (The scope block may name it as a guarded entry with its
        # reviewed reason; the rows must not contain it.)
        conformance_file = (
            REPO_ROOT
            / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_conformance.sysml"
        )
        witness_file = REPO_ROOT / po22.VERIFICATION_MODEL_FILE
        assert "MethodEvaluationScope" in conformance_file.read_text(encoding="utf-8")
        assert "MethodEvaluationScope" in witness_file.read_text(encoding="utf-8")
        assert "MethodEvaluationScope" not in _row_blob(pair)

    def test_blocked_and_rename_identities_stay_absent(self, pair) -> None:
        # The ontology still declares these relationships (discoverable
        # representation), yet the rows contain neither a row nor a leaked
        # field for them: representation existence never overrides admission.
        ontology = yaml.safe_load(
            (REPO_ROOT / po22.ONTOLOGY_PATH).read_text(encoding="utf-8")
        )
        relationships = ontology["relationships"]
        for identity in (
            "realizedBy",
            "specifiesFunction",
            "hasRelevantEvidenceContract",
            "derivesNeedFromConcern",
        ):
            assert identity in relationships
        rendered = _row_blob(pair)
        for identity in (
            "realizedBy",
            "specifiesFunction",
            "hasRelevantEvidenceContract",
            "derivesNeedFromConcern",
        ):
            assert f'"{identity}"' not in rendered

    def test_o2_3_identities_remain_absent(self, pair) -> None:
        rendered = _row_blob(pair)
        for identity in pv.O2_SEQUENCING["o2.3"]:
            assert f'"{identity}"' not in rendered


# ---------------------------------------------------------------------------
# 4. Adversarial fixtures
# ---------------------------------------------------------------------------


class TestAdversarial:
    def test_a_extra_model_vocabulary_does_not_expand_output(
        self, tmp_path, stubbed_gate
    ) -> None:
        extra = (
            "\n  verification <'VC-AEBS-009D-99'>extraVerification"
            " : ConsciousOverrideVerification {\n"
            "    @VerificationMethod{ kind = test; }\n"
            "  }\n"
        )

        def mutate(text: str) -> str:
            return text.rstrip() + extra

        root = _fixture_root(
            tmp_path, file_mutators={po22.VERIFICATION_MODEL_FILE: mutate}
        )
        built = po22.build_pair_o22(root, source_revision="f" * 40)
        rows = list(built["projection"]["concepts"]) + list(
            built["projection"]["predicates"]
        )
        assert tuple(row["identity"] for row in rows) == po22.O22_ADMITTED_IDENTITIES

    def test_b_missing_admitted_declaration_fails(self, tmp_path, stubbed_gate) -> None:
        def mutate(text: str) -> str:
            return _remove_declaration(text, "part def ProductLineMemberProduct")

        root = _fixture_root(tmp_path, file_mutators={_PRODUCT_LINE_FILE: mutate})
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)

    def test_b2_missing_verification_definition_fails(
        self, tmp_path, stubbed_gate
    ) -> None:
        def mutate(text: str) -> str:
            return text.replace(
                "verification def <'VC-AEBS-009D-DE'>", "verification <'VC-AEBS-009D-DE'>"
            )

        root = _fixture_root(
            tmp_path, file_mutators={po22.VERIFICATION_MODEL_FILE: mutate}
        )
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)

    def test_c_ambiguous_grounding_fails(self, tmp_path, stubbed_gate) -> None:
        def mutate(text: str) -> str:
            block = _declaration_block(text, "part def ProductLineMemberProduct")
            return text[: block[1]] + "\n" + text[block[0] : block[1]]

        root = _fixture_root(tmp_path, file_mutators={_PRODUCT_LINE_FILE: mutate})
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)

    def test_d_same_name_wrong_structural_identity_fails(
        self, tmp_path, stubbed_gate
    ) -> None:
        def mutate(text: str) -> str:
            return text.replace(
                "verification def <'VC-AEBS-009D-DE'>ConsciousOverrideVerification",
                "action def <'VC-AEBS-009D-DE'>ConsciousOverrideVerification",
            )

        root = _fixture_root(
            tmp_path, file_mutators={po22.VERIFICATION_MODEL_FILE: mutate}
        )
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)

    def test_d2_foreign_usage_lineage_fails(self, tmp_path, stubbed_gate) -> None:
        def mutate(text: str) -> str:
            return text.replace(
                "overrideFalseControlVerification : ConsciousOverrideVerification",
                "overrideFalseControlVerification : SomeOtherVerification",
            )

        root = _fixture_root(
            tmp_path, file_mutators={po22.VERIFICATION_MODEL_FILE: mutate}
        )
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)

    def test_e_wrong_metaclass_shape_fails(self, tmp_path, stubbed_gate) -> None:
        def contract_mutator(contract):
            contract["classes"]["VerificationCase"]["kernel"] = {
                "file": _PRODUCT_LINE_FILE,
                "declaration": "part def ProductLineMemberProduct",
            }

        root = _fixture_root(tmp_path, contract_mutator=contract_mutator)
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)

    def test_f_no_objective_witnesses_fails(self, tmp_path, stubbed_gate) -> None:
        def mutate(text: str) -> str:
            start = text.find("objective evidenceObjective")
            assert start != -1
            brace = text.find("{", start)
            close = po22._matching_brace(text, brace)
            return text[:start] + text[close + 1 :]

        root = _fixture_root(
            tmp_path, file_mutators={po22.VERIFICATION_MODEL_FILE: mutate}
        )
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)

    def test_g_o1_data_cannot_manufacture_a_row(self, tmp_path, stubbed_gate) -> None:
        plain = _fixture_root(tmp_path / "a")
        decoy = _fixture_root(tmp_path / "b", with_decoy_o1=True)
        plain_built = po22.build_pair_o22(plain, source_revision="f" * 40)
        decoy_built = po22.build_pair_o22(decoy, source_revision="f" * 40)
        assert po22.canonical_json(plain_built) == po22.canonical_json(decoy_built)

    def test_g2_generation_without_any_o1_directory(self, tmp_path, stubbed_gate) -> None:
        root = _fixture_root(tmp_path)
        assert not any((root / path).exists() for path in O1_ARTIFACT_PATHS)
        built = po22.build_pair_o22(root, source_revision="f" * 40)
        rows = list(built["projection"]["concepts"]) + list(
            built["projection"]["predicates"]
        )
        assert tuple(row["identity"] for row in rows) == po22.O22_ADMITTED_IDENTITIES
        rendered = po22.canonical_json(built["projection"])
        for field in O1_GOVERNANCE_FIELDS:
            assert f'"{field}"' not in rendered

    def test_contract_domain_drift_fails(self, tmp_path, stubbed_gate) -> None:
        def contract_mutator(contract):
            contract["relationships"]["hasSubject"]["domain"] = "Need"

        root = _fixture_root(tmp_path, contract_mutator=contract_mutator)
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)

    def test_contract_witness_drift_fails(self, tmp_path, stubbed_gate) -> None:
        def contract_mutator(contract):
            contract["relationships"]["verifiedBy"]["sysml_mapping"][
                "membership_types"
            ] = ["Dependency"]

        root = _fixture_root(tmp_path, contract_mutator=contract_mutator)
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)

    def test_contract_strategy_drift_fails(self, tmp_path, stubbed_gate) -> None:
        def contract_mutator(contract):
            contract["relationships"]["verifiedBy"]["sysml_mapping"][
                "strategy"
            ] = "dependency"

        root = _fixture_root(tmp_path, contract_mutator=contract_mutator)
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)

    def test_anchor_not_file_mapped_fails(self, tmp_path, stubbed_gate) -> None:
        def contract_mutator(contract):
            contract["classes"]["Requirement"]["kernel"] = {
                "native": "some native grounding"
            }

        root = _fixture_root(tmp_path, contract_mutator=contract_mutator)
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)

    @pytest.mark.parametrize(
        "baseline_path",
        (
            po22.BASELINE_PROJECTION_V1_PATH,
            po22.BASELINE_PROFILE_V1_PATH,
        ),
    )
    def test_missing_baseline_fails(
        self, tmp_path, stubbed_gate, baseline_path
    ) -> None:
        root = _fixture_root(tmp_path)
        (root / baseline_path).unlink()
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)

    @pytest.mark.parametrize(
        "baseline_path, wrong_schema",
        (
            (po22.BASELINE_PROJECTION_V1_PATH, "de4sdv.api-representation-profile.v1"),
            (po22.BASELINE_PROFILE_V1_PATH, "de4sdv.semantic-projection.v1"),
        ),
    )
    def test_swapped_schema_baseline_fails(
        self, tmp_path, stubbed_gate, baseline_path, wrong_schema
    ) -> None:
        # Each extension must extend its OWN baseline schema: a projection
        # baseline carrying the profile schema (or vice versa) fails closed.
        root = _fixture_root(tmp_path)
        path = root / baseline_path
        document = json.loads(path.read_text(encoding="utf-8"))
        document["schema"] = wrong_schema
        path.write_text(json.dumps(document), encoding="utf-8")
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)

    def test_revisionless_baseline_fails(self, tmp_path, stubbed_gate) -> None:
        root = _fixture_root(tmp_path)
        path = root / po22.BASELINE_PROFILE_V1_PATH
        document = json.loads(path.read_text(encoding="utf-8"))
        document["binding"].pop("source_revision")
        path.write_text(json.dumps(document), encoding="utf-8")
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)

    @pytest.mark.parametrize(
        "baseline_path, pin_key",
        (
            (po22.BASELINE_PROJECTION_V1_PATH, "projection"),
            (po22.BASELINE_PROFILE_V1_PATH, "profile"),
        ),
    )
    def test_edited_baseline_is_detected_by_the_gate(
        self, tmp_path, stubbed_gate, baseline_path, pin_key
    ) -> None:
        root = _fixture_root(tmp_path)
        built = po22.build_pair_o22(root, source_revision="f" * 40)
        original = built[pin_key]["extends"]["artifact_digest"]
        path = root / baseline_path
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        rebuilt = po22.build_pair_o22(root, source_revision="f" * 40)
        assert rebuilt[pin_key]["extends"]["artifact_digest"] != original

    def test_compat_gate_rejects_profile_that_redefines_semantics(
        self, tmp_path, stubbed_gate
    ) -> None:
        root = _fixture_root(tmp_path)
        built = po22.build_pair_o22(root, source_revision="f" * 40)
        projection = built["projection"]
        profile = built["profile"]
        entry = {e["for_identity"]: e for e in profile["profiles"]}["verifiedBy"]
        entry["semantic_contract_echo"]["domain"] = "Need"
        with pytest.raises(po22.ProjectionO22Error):
            po22.assert_profile_compatible_o22(projection, profile)

    def test_compat_gate_rejects_support_promotion(self, tmp_path, stubbed_gate) -> None:
        root = _fixture_root(tmp_path)
        built = po22.build_pair_o22(root, source_revision="f" * 40)
        projection = built["projection"]
        promoted = json.loads(json.dumps(built["projection"]))
        promoted["predicates"][0]["support_state"] = "supported"
        with pytest.raises(po22.ProjectionO22Error):
            po22.assert_profile_compatible_o22(promoted, built["profile"])

    def test_missing_verification_witness_file_fails(self, tmp_path, stubbed_gate) -> None:
        root = _fixture_root(tmp_path)
        (root / po22.VERIFICATION_MODEL_FILE).unlink()
        with pytest.raises(po22.ProjectionO22Error):
            po22.build_pair_o22(root, source_revision="f" * 40)


# ---------------------------------------------------------------------------
# 5. O2.1 / v0 preservation and runtime independence
# ---------------------------------------------------------------------------


class TestPreservationAndRuntimeIndependence:
    def test_v1_gate_still_green_on_this_checkout(self) -> None:
        assert pv.run_check_errors(REPO_ROOT) == []

    def test_projection_v0_byte_unchanged_since_v1_baseline(self) -> None:
        baseline_revision = json.loads(
            (REPO_ROOT / po22.BASELINE_PROJECTION_V1_PATH).read_text(encoding="utf-8")
        )["binding"]["source_revision"]
        for rel in ("de4sdv/semantic/projection.py",):
            blob = subprocess.run(
                ["git", "show", f"{baseline_revision}:{rel}"],
                cwd=REPO_ROOT,
                capture_output=True,
                check=True,
            ).stdout
            assert (REPO_ROOT / rel).read_bytes() == blob

    def test_no_runtime_module_imports_or_reads_v11(self) -> None:
        offenders: list[str] = []
        for path in sorted((REPO_ROOT / "de4sdv").rglob("*.py")):
            rel = path.relative_to(REPO_ROOT).as_posix()
            if rel == "de4sdv/semantic/projection_o22.py":
                continue
            if rel == "de4sdv/semantic/projection_o23.py":
                # build-time O2.3 generator (documented, same pattern)
                continue
            if rel == "de4sdv/semantic/o3_equivalence.py":
                # O3 readiness tooling (documented, same pattern): read-only
                # planning/evidence module for the future cutover.
                continue
            if rel == "de4sdv/semantic/o3_bundle.py":
                # O3 candidate authority bundle (documented, same pattern):
                # Stage-A machinery, candidate path only.
                continue
            text = path.read_text(encoding="utf-8")
            if "projection_o22" in text or "semantic-projection-v1.1" in text:
                offenders.append(rel)
        assert offenders == []

    def test_support_rule_is_the_established_one(self) -> None:
        assert po22.SUPPORT_STATE_VOCABULARY_ONLY == "vocabulary-only"
        # The O2.2-only support vocabulary was removed; only the established
        # rule (vocabulary-only without exact-revision closure evidence)
        # remains, and no promotion input exists.
        assert not hasattr(po22, "O22_SUPPORT_STATES")
        assert not hasattr(po22, "SUPPORT_STATE_NATIVE_GROUNDED")
        assert not hasattr(po22, "SUPPORT_STATE_IMPLEMENTED_MAPPING")
        assert po22.RUNTIME_MAPPING_STATE_EXISTING_NOT_AUTHORITY == (
            "existing-not-authority"
        )

    def test_ontology_authority_not_retired(self) -> None:
        assert (REPO_ROOT / po22.ONTOLOGY_PATH).is_file()
        ontology = yaml.safe_load(
            (REPO_ROOT / po22.ONTOLOGY_PATH).read_text(encoding="utf-8")
        )
        assert "relationships" in ontology and "classes" in ontology


# ---------------------------------------------------------------------------
# 7. Committed artifacts, end-to-end gate behavior, repository wiring
# ---------------------------------------------------------------------------

# W2 pilot 2 rebind: the v1.1 artifacts' source revision moved to the W2
# stage-A revision because the model-input doc parity change altered a bound
# input digest. A post-squash rebind follow-up (PR #251 pattern) moves this,
# and the artifact binding, to the permanent main revision after merge.
COMMITTED_SOURCE_REVISION = "712b8c2aa5544247cce0f9901640ddcc9d3daf7d"


def _git_backed_repo(tmp_path: Path) -> tuple[Path, str, str]:
    """Synthetic real Git checkout for end-to-end gate tests.

    Copies the fixture inputs, initializes a real repository, commits the
    inputs as revision R1, rebinds both copied v1 baselines to R1, commits
    that as R2, regenerates the v1.1 artifacts bound to R2, and commits them
    (HEAD = R3). Returns ``(root, R2, R3)``. The gate then runs against a real
    ancestor chain with real blobs — no stubbing.
    """
    root = _fixture_root(tmp_path)

    def git(*args: str) -> None:
        subprocess.run(
            ["git", *args], cwd=root, check=True, capture_output=True
        )

    def head() -> str:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "-q")
    git("config", "user.name", "gate-test")
    git("config", "user.email", "gate-test@local")
    git("add", "-A")
    git("commit", "-q", "-m", "inputs")
    r1 = head()
    for baseline_path in (
        po22.BASELINE_PROJECTION_V1_PATH,
        po22.BASELINE_PROFILE_V1_PATH,
    ):
        path = root / baseline_path
        document = json.loads(path.read_text(encoding="utf-8"))
        document["binding"]["source_revision"] = r1
        path.write_text(json.dumps(document), encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "rebind baselines to inputs revision")
    r2 = head()
    built = po22.build_pair_o22(root, source_revision=r2)
    (root / po22.PROJECTION_V11_JSON_PATH).write_text(
        po22.canonical_json(built["projection"]), encoding="utf-8"
    )
    (root / po22.PROFILE_V11_JSON_PATH).write_text(
        po22.canonical_json(built["profile"]), encoding="utf-8"
    )
    git("add", "-A")
    git("commit", "-q", "-m", "artifacts bound to inputs revision")
    return root, r2, head()


class TestCommittedArtifacts:
    def test_committed_artifacts_match_regeneration(self) -> None:
        assert po22.run_check_errors_o22(REPO_ROOT) == []

    def test_committed_artifacts_exist_and_parse(self) -> None:
        projection = json.loads(
            (REPO_ROOT / po22.PROJECTION_V11_JSON_PATH).read_text(encoding="utf-8")
        )
        profile = json.loads(
            (REPO_ROOT / po22.PROFILE_V11_JSON_PATH).read_text(encoding="utf-8")
        )
        assert projection["schema"] == po22.PROJECTION_V11_SCHEMA
        assert profile["schema"] == po22.PROFILE_V11_SCHEMA
        for document in (projection, profile):
            assert document["binding"]["source_revision"] == (
                COMMITTED_SOURCE_REVISION
            )
            assert document["binding"]["api_binding"]["status"] == "unclaimed"
        rows = list(projection["concepts"]) + list(projection["predicates"])
        assert tuple(row["identity"] for row in rows) == po22.O22_ADMITTED_IDENTITIES
        assert all(row["support_state"] == "vocabulary-only" for row in rows)
        assert projection["extends"]["artifact"] == po22.BASELINE_PROJECTION_V1_PATH
        assert profile["extends"]["artifact"] == po22.BASELINE_PROFILE_V1_PATH
        assert projection["extends"] != profile["extends"]

    def test_committed_pins_match_baseline_bytes(self) -> None:
        import hashlib

        for document_path, baseline_path in (
            (po22.PROJECTION_V11_JSON_PATH, po22.BASELINE_PROJECTION_V1_PATH),
            (po22.PROFILE_V11_JSON_PATH, po22.BASELINE_PROFILE_V1_PATH),
        ):
            document = json.loads(
                (REPO_ROOT / document_path).read_text(encoding="utf-8")
            )
            pin = document["extends"]
            expected = "sha256:" + hashlib.sha256(
                (REPO_ROOT / baseline_path).read_bytes()
            ).hexdigest()
            assert pin["artifact_digest"] == expected, document_path
            baseline = json.loads(
                (REPO_ROOT / baseline_path).read_text(encoding="utf-8")
            )
            assert pin["source_revision"] == baseline["binding"]["source_revision"]

    def test_committed_projection_separation_remains_clean(self) -> None:
        projection = json.loads(
            (REPO_ROOT / po22.PROJECTION_V11_JSON_PATH).read_text(encoding="utf-8")
        )
        rows = list(projection["concepts"]) + list(projection["predicates"])
        blob = json.dumps(rows)
        for banned in (
            "memberElement",
            "reference_property",
            "member_property",
            "owner_types",
            "owner_membership_types",
            "element_types",
            "ReferenceSubsetting",
            "Subclassification",
            "Subsetting",
            "serializer",
            "shadow",
            "metaclass",
            "implied",
        ):
            assert banned not in blob, banned

    def test_editing_either_artifact_fails_the_gate(self, tmp_path) -> None:
        root, revision, head = _git_backed_repo(tmp_path)
        assert head != revision
        assert po22.run_check_errors_o22(root) == []
        for artifact_path in (
            po22.PROJECTION_V11_JSON_PATH,
            po22.PROFILE_V11_JSON_PATH,
        ):
            path = root / artifact_path
            original = path.read_text(encoding="utf-8")
            path.write_text(original + "\n", encoding="utf-8")
            errors = po22.run_check_errors_o22(root)
            assert errors, artifact_path
            assert any("differs from regeneration" in error for error in errors)
            path.write_text(original, encoding="utf-8")
            assert po22.run_check_errors_o22(root) == []

    def test_gate_reports_missing_artifacts_when_absent(self, tmp_path) -> None:
        # The gate must never treat missing artifacts as success.
        root, revision, head = _git_backed_repo(tmp_path)
        (root / po22.PROJECTION_V11_JSON_PATH).unlink()
        errors = po22.run_check_errors_o22(root)
        assert errors == [
            f"semantic projection v1.1 missing: {po22.PROJECTION_V11_JSON_PATH}"
        ]


class TestRepositoryGateWiring:
    """The v1.1 gate owns its own failure attribution in ``check_repo``."""

    def test_check_repo_fails_when_o22_gate_fails(self) -> None:
        from unittest import mock

        from scripts import check_repo

        with mock.patch.object(
            check_repo, "find_duplicate_global_packages", return_value={}
        ), mock.patch.object(
            check_repo.validate_aebs_executable_bench, "validate_bench", return_value=[]
        ), mock.patch.object(
            check_repo.check_model_sync, "run_all_checks", return_value=[]
        ), mock.patch.object(
            check_repo.generate_scenario_manifest, "run_check_errors", return_value=[]
        ), mock.patch.object(
            check_repo.check_naming, "run_all_checks", return_value=[]
        ), mock.patch.object(
            check_repo.generate_semantic_projection_v1,
            "run_check_errors",
            return_value=[],
        ), mock.patch.object(
            check_repo.generate_semantic_authority_inventory,
            "run_check_errors",
            return_value=[],
        ), mock.patch.object(
            check_repo.generate_semantic_projection_o23,
            "run_check_errors_o23",
            return_value=[],
        ), mock.patch.object(
            check_repo.generate_semantic_projection_o22,
            "run_check_errors_o22",
            return_value=["sentinel projection v1.1 error"],
        ):
            assert check_repo.main() == 1

    def test_check_repo_passes_when_all_gates_pass(self) -> None:
        from unittest import mock

        from scripts import check_repo

        with mock.patch.object(
            check_repo, "find_duplicate_global_packages", return_value={}
        ), mock.patch.object(
            check_repo.validate_aebs_executable_bench, "validate_bench", return_value=[]
        ), mock.patch.object(
            check_repo.check_model_sync, "run_all_checks", return_value=[]
        ), mock.patch.object(
            check_repo.generate_scenario_manifest, "run_check_errors", return_value=[]
        ), mock.patch.object(
            check_repo.check_naming, "run_all_checks", return_value=[]
        ), mock.patch.object(
            check_repo.generate_semantic_projection_v1,
            "run_check_errors",
            return_value=[],
        ), mock.patch.object(
            check_repo.generate_semantic_projection_o22,
            "run_check_errors_o22",
            return_value=[],
        ), mock.patch.object(
            check_repo.generate_semantic_projection_o23,
            "run_check_errors_o23",
            return_value=[],
        ), mock.patch.object(
            check_repo.generate_semantic_authority_inventory,
            "run_check_errors",
            return_value=[],
        ):
            assert check_repo.main() == 0

    def test_check_repo_actually_invokes_the_o22_gate(self) -> None:
        # A pass-through spy proves check_repo calls the v1.1 gate (rather
        # than the test suite accidentally bypassing it).
        from unittest import mock

        from scripts import check_repo

        calls: list[int] = []
        original = check_repo.generate_semantic_projection_o22.run_check_errors_o22

        def spy(root):
            calls.append(1)
            return original(root)

        with mock.patch.object(
            check_repo.generate_semantic_projection_o22,
            "run_check_errors_o22",
            side_effect=spy,
        ):
            result = check_repo.main()
        assert calls, "check_repo did not invoke the O2.2 gate"
        assert result == 0
