"""Machine locks for the native-grounding projection layer.

The layer is governed by review Deliverable 8 wave 3 (native/library
projection rows over already-native constructs) and the ontology identity
register rows for the admitted identities. These tests lock:

* the admitted set is EXACTLY the reviewed safe subset (eight identities)
  with per-row flags equal to the reviewed values;
* the excluded set carries a reason for every considered-but-not-admitted
  row and contains the hard gates that must never be admitted;
* no identity of the frozen records (the thirteen of projection
  v1/v1.1/v1.2) is admitted or emitted;
* generation is deterministic and read-only; the committed pair equals
  regeneration from current governed inputs without a live Git binding;
* support stays vocabulary-only, traversal is false everywhere, and no
  support promotion can slip through the generation path.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from de4sdv.semantic import native_grounding_projection as native

ROOT = Path(__file__).resolve().parents[1]

REVIEWED_ADMITTED: dict[str, dict[str, bool | str]] = {
    "VariationPoint": {
        "category": "native",
        "projection_required": False,
        "api_profile_required": True,
        "traversal_required": False,
    },
    "Variant": {
        "category": "native",
        "projection_required": False,
        "api_profile_required": True,
        "traversal_required": False,
    },
    "Concern": {
        "category": "native",
        "projection_required": True,
        "api_profile_required": False,
        "traversal_required": False,
    },
    "Viewpoint": {
        "category": "native",
        "projection_required": True,
        "api_profile_required": False,
        "traversal_required": False,
    },
    "View": {
        "category": "native",
        "projection_required": True,
        "api_profile_required": False,
        "traversal_required": False,
    },
    "VerificationMethod": {
        "category": "library-mapped-native",
        "projection_required": False,
        "api_profile_required": False,
        "traversal_required": False,
    },
    "usesVerificationMethod": {
        "category": "library-mapped-native",
        "projection_required": False,
        "api_profile_required": False,
        "traversal_required": False,
    },
    "IncrementSize": {
        "category": "model-resident-vocabulary",
        "projection_required": True,
        "api_profile_required": False,
        "traversal_required": False,
    },
}

HARD_GATES = (
    "allocatedTo",
    "EvidenceStatus",
    "variesAt",
    "FeatureConfiguration",
    "instantiatesCanonicalArchitecture",
)


@pytest.fixture(scope="module")
def manifest() -> dict:
    return native.load_admission(ROOT / native.ADMISSION_PATH)


@pytest.fixture(scope="module")
def artifacts() -> dict:
    projection = json.loads(
        (ROOT / native.PROJECTION_PATH).read_text(encoding="utf-8")
    )
    profile = json.loads((ROOT / native.PROFILE_PATH).read_text(encoding="utf-8"))
    return {"projection": projection, "profile": profile}


def test_admitted_set_is_exactly_the_reviewed_safe_subset(manifest: dict) -> None:
    admitted = {row["identity"] for row in manifest["admitted"]}
    assert admitted == set(REVIEWED_ADMITTED)


@pytest.mark.parametrize("identity", sorted(REVIEWED_ADMITTED))
def test_per_row_flags_match_reviewed_values(manifest: dict, identity: str) -> None:
    row = next(r for r in manifest["admitted"] if r["identity"] == identity)
    expected = REVIEWED_ADMITTED[identity]
    assert row["category"] == expected["category"]
    assert bool(row["projection_required"]) is expected["projection_required"]
    assert bool(row["api_profile_required"]) is expected["api_profile_required"]
    assert bool(row["traversal_required"]) is expected["traversal_required"]
    assert row["support"] == "vocabulary-only"
    for field in ("construct", "exact_fit", "standard_construct", "claim_boundary"):
        assert str(row[field]).strip(), f"{identity}: {field} must be non-empty"


def test_excluded_rows_all_carry_reasons_and_cover_hard_gates(manifest: dict) -> None:
    excluded = {row["identity"]: row["reason"] for row in manifest["excluded"]}
    for identity, reason in excluded.items():
        assert str(reason).strip(), f"{identity}: reason required"
    for gated in HARD_GATES:
        assert gated in excluded, f"hard gate {gated} must stay excluded"


def test_admitted_and_excluded_are_disjoint(manifest: dict) -> None:
    admitted = {row["identity"] for row in manifest["admitted"]}
    excluded = {row["identity"] for row in manifest["excluded"]}
    assert admitted & excluded == set()


# Per-row precision for the excluded rows: every considered-but-excluded row is
# recorded in the admission manifest with its concrete reason, and no aggregate
# assertion lets a row slip in or out silently.

#: The admitted native and library-mapped rows (``IncrementSize`` is the
#: model-resident vocabulary row admitted with them).
NATIVE_AND_LIBRARY_ROWS: tuple[str, ...] = (
    "VariationPoint",
    "Variant",
    "Concern",
    "Viewpoint",
    "View",
    "VerificationMethod",
    "usesVerificationMethod",
)

#: Excluded rows pinned with a reason keyword (from the admission manifest).
EXCLUDED_REASON_KEYWORDS: dict[str, str] = {
    "EvidenceStatus": "decision-4",
    "hasEvidenceStatus": "decision-4",
    "allocatedTo": "W7-held",
    "variesAt": "PLE-Q/S",
    "FeatureConfiguration": "decision-9",
    "selectsFeature": "decision-9",
    "appliesToMemberProduct": "decision-9",
    "includesCommonCapability": "decision-9",
    "selectsVariant": "decision-9",
    "instantiatesCanonicalArchitecture": "decision-10",
    "Interface": "decision-5",
    "ValidationScenario": "validatedBy",
    "hasStakeholder": "decision-11",
    "specifiesFeature": "PLE-Q/S",
    "specifiesCommonCapability": "PLE-Q/S",
    "recordsGap": "removed register row",
    "recordsAssumption": "removed register row",
    "addressesConcern": "removed register row",
    "selectedViewpoint": "removed register row",
    "producesView": "removed register row",
    "EvidenceArtifact": "W5 batch 3 treated",
    "hasEvidence": "W5 batch 3 treated",
    "capturedInBaseline": "W5 batch 3 treated",
    # The class-definition admission treated these two rows after this manifest
    # was written; the reasons were refreshed to record the treatment while
    # the rows remain outside this admission (their representation belongs
    # to the class-definition layer).
    "Scenario": "Definition admission batch 1 treated",
    "CommonCapability": "decision-14",
    "Feature": "decision-14",
    "MethodEvaluationScope": "decision-7",
    "ProductLineCharacteristic": "Definition admission batch 1 treated",
    "Stakeholder": "decision-11",
    "AssuranceClaim": "decision-3",
    "ArchitectureElement": "decision-5",
    "Function": "decision-5",
    "LogicalElement": "decision-5",
    "PhysicalElement": "decision-5",
    "AcceptanceCriterion": "decision-6",
    "hasAcceptanceCriterion": "decision-6",
    "EvidenceContract": "evidence-lineage",
    "hasRelevantEvidenceContract": "evidence-lineage",
    "constrainedBy": "decision-2",
    "realizedBy": "decision-1",
    "deployedTo": "decision-1",
    "validatedBy": "decision-1",
    "supportedByEvidence": "decision-3",
    "TraceLink": "decision-8",
    "RequiredTraceChain": "decision-8",
}


def test_excluded_matrix_matches_the_admission_manifest(manifest: dict) -> None:
    manifest_excluded = {row["identity"]: row["reason"] for row in manifest["excluded"]}
    assert set(manifest_excluded) == set(EXCLUDED_REASON_KEYWORDS)
    for identity, keyword in EXCLUDED_REASON_KEYWORDS.items():
        assert keyword in manifest_excluded[identity], identity


def test_admitted_rows_are_disjoint_from_excluded(manifest: dict) -> None:
    admitted = {row["identity"] for row in manifest["admitted"]}
    excluded = {row["identity"] for row in manifest["excluded"]}
    assert admitted == set(NATIVE_AND_LIBRARY_ROWS) | {"IncrementSize"}
    assert admitted & excluded == set()


def test_frozen_projection_row_identities_are_never_admitted(manifest: dict) -> None:
    admitted = {row["identity"] for row in manifest["admitted"]}
    assert admitted & set(native.FROZEN_PROJECTION_ROW_IDENTITIES) == set()
    # The frozen list itself must equal the actual committed v1/v1.1/v1.2 rows.
    actual: list[str] = []
    for name in ("semantic-projection-v1.json", "semantic-projection-v1.1.json", "semantic-projection-v1.2.json"):
        document = json.loads(
            (ROOT / "de4sdv/semantic/contract-data/frozen-records" / name).read_text(encoding="utf-8")
        )
        actual.extend(r["identity"] for r in document.get("concepts", []))
        actual.extend(r["identity"] for r in document.get("predicates", []))
    assert sorted(actual) == sorted(native.FROZEN_PROJECTION_ROW_IDENTITIES)


def test_served_frozen_identities_are_never_admitted(manifest: dict) -> None:
    from de4sdv.semantic.model_contract import FROZEN_RECORD_IDENTITIES as SERVED_FROZEN_IDENTITIES

    admitted = {row["identity"] for row in manifest["admitted"]}
    assert admitted & set(SERVED_FROZEN_IDENTITIES) == set()
    assert len(SERVED_FROZEN_IDENTITIES) == 13


def test_witnesses_exist_in_the_model() -> None:
    manifest = native.load_admission(ROOT / native.ADMISSION_PATH)
    native.verify_witnesses(ROOT, manifest)  # raises on any missing construct


def test_projection_rows_are_exactly_the_admitted_set(artifacts: dict) -> None:
    rows = artifacts["projection"]["rows"]
    assert [r["identity"] for r in rows] == [
        row["identity"] for row in native.load_admission(
            ROOT / native.ADMISSION_PATH
        )["admitted"]
    ]


@pytest.mark.parametrize("identity", sorted(REVIEWED_ADMITTED))
def test_projection_row_outputs_match_reviewed_flags(
    artifacts: dict, identity: str
) -> None:
    row = next(r for r in artifacts["projection"]["rows"] if r["identity"] == identity)
    expected = REVIEWED_ADMITTED[identity]
    # Emitted outputs must EQUAL the reviewed flags: a grounding record for a
    # `projection_required = false` row is not a projection output.
    assert row["outputs"]["projection_row"] is expected["projection_required"]
    assert row["outputs"]["api_profile_entry"] is expected["api_profile_required"]
    assert row["outputs"]["traversal"] is expected["traversal_required"]
    assert row["support"] == "vocabulary-only"
    assert row["grounding"]["witness"]["found"] is True
    assert row["claim_boundary"].strip()
    # No duplicated semantic-kind field: the governed category carries the
    # distinction (removed to prevent misclassification).
    assert "semantic_kind" not in row


def test_no_frozen_identity_is_emitted(artifacts: dict) -> None:
    from de4sdv.semantic.model_contract import FROZEN_RECORD_IDENTITIES as SERVED_FROZEN_IDENTITIES

    emitted = {row["identity"] for row in artifacts["projection"]["rows"]}
    assert emitted & set(native.FROZEN_PROJECTION_ROW_IDENTITIES) == set()
    assert emitted & set(SERVED_FROZEN_IDENTITIES) == set()


def test_profile_entries_are_exactly_the_api_profile_rows(artifacts: dict) -> None:
    expected = sorted(
        identity
        for identity, spec in REVIEWED_ADMITTED.items()
        if spec["api_profile_required"]
    )
    entries = artifacts["profile"]["entries"]
    assert sorted(e["identity"] for e in entries) == expected
    for entry in entries:
        representation = entry["representation"]
        assert representation["mechanics"].strip()
        assert representation["toolchain"]["syside_modeler_cli"].strip()


def test_pair_has_no_live_source_binding() -> None:
    # This cleanup retires only live binding assertions, not the frozen O2 locks above.
    generated = native.build_artifact_pair(ROOT)
    for document in generated.values():
        assert "binding" not in document
    assert all(
        "bound_revision" not in row["review_ref"]
        for row in generated["projection"]["rows"]
    )


def test_regeneration_is_deterministic() -> None:
    first = native.build_artifact_pair(ROOT)
    second = native.build_artifact_pair(ROOT, source_revision="0" * 40)
    assert native.canonical_json(first["projection"]) == native.canonical_json(
        second["projection"]
    )
    assert native.canonical_json(first["profile"]) == native.canonical_json(
        second["profile"]
    )


def test_check_passes_on_the_committed_tree() -> None:
    assert native.run_check_errors(ROOT) == []


EXPECTED_PROJECTION_OUTPUTS = ["Concern", "IncrementSize", "View", "Viewpoint"]
EXPECTED_API_PROFILE_OUTPUTS = ["Variant", "VariationPoint"]
EXPECTED_GROUNDING_RECORD_ONLY = ["VerificationMethod", "usesVerificationMethod"]


def test_projection_outputs_are_exactly_the_reviewed_set(artifacts: dict) -> None:
    outputs = sorted(
        row["identity"]
        for row in artifacts["projection"]["rows"]
        if row["outputs"]["projection_row"]
    )
    assert outputs == EXPECTED_PROJECTION_OUTPUTS
    assert artifacts["projection"]["scope"]["projection_outputs"] == outputs


def test_api_profile_outputs_are_exactly_the_reviewed_set(artifacts: dict) -> None:
    outputs = sorted(
        row["identity"]
        for row in artifacts["projection"]["rows"]
        if row["outputs"]["api_profile_entry"]
    )
    assert outputs == EXPECTED_API_PROFILE_OUTPUTS
    assert artifacts["projection"]["scope"]["api_profile_outputs"] == outputs
    assert sorted(e["identity"] for e in artifacts["profile"]["entries"]) == outputs


def test_grounding_record_only_rows_emit_no_projection_output(artifacts: dict) -> None:
    only = sorted(
        row["identity"]
        for row in artifacts["projection"]["rows"]
        if not row["outputs"]["projection_row"]
        and not row["outputs"]["api_profile_entry"]
    )
    assert only == EXPECTED_GROUNDING_RECORD_ONLY
    assert artifacts["projection"]["scope"]["grounding_record_only"] == only


def test_no_traversal_outputs_anywhere(artifacts: dict) -> None:
    outputs = [
        row["identity"]
        for row in artifacts["projection"]["rows"]
        if row["outputs"]["traversal"]
    ]
    assert outputs == []
    assert artifacts["projection"]["scope"]["traversal_outputs"] == []
    assert all(
        row["outputs"]["traversal"] is False
        for row in artifacts["projection"]["rows"]
    )


def test_provenance_classification_separates_model_and_tooling(artifacts: dict) -> None:
    # Binding classification is retired; preserve the model/tooling distinction
    # at the actual semantic-witness and representation-mechanics locations.
    witness_files = sorted(
        {
            row["witness"]["file"]
            for row in native.load_admission(
                ROOT / native.ADMISSION_PATH
            )["admitted"]
        }
    )
    actual_witnesses = sorted({
        row["grounding"]["witness"]["file"]
        for row in artifacts["projection"]["rows"]
    })
    assert actual_witnesses == witness_files
    assert native.SYSIDE_WORKFLOW_PATH not in actual_witnesses
    for path in actual_witnesses:
        assert path.endswith(".sysml")
    for entry in artifacts["profile"]["entries"]:
        assert entry["representation"]["toolchain"]["syside_modeler_cli"] == (
            native.read_syside_pin(ROOT)
        )


def test_categories_are_not_flattened(artifacts: dict) -> None:
    by_identity = {row["identity"]: row for row in artifacts["projection"]["rows"]}
    assert by_identity["IncrementSize"]["category"] == "model-resident-vocabulary"
    assert by_identity["VerificationMethod"]["category"] == "library-mapped-native"
    assert (
        by_identity["usesVerificationMethod"]["category"] == "library-mapped-native"
    )
    for identity in ("VariationPoint", "Variant", "Concern", "Viewpoint", "View"):
        assert by_identity[identity]["category"] == "native"


# --- fail-closed negatives -------------------------------------------------


def _mutated_manifest(manifest: dict, mutate) -> dict:
    clone = copy.deepcopy(manifest)
    mutate(clone)
    return clone


def test_extra_admission_fails_closed(manifest: dict) -> None:
    def mutate(clone: dict) -> None:
        extra = copy.deepcopy(clone["admitted"][0])
        extra["identity"] = "SomeUnreviewedIdentity"
        clone["admitted"].append(extra)

    with pytest.raises(native.NativeGroundingError):
        native.validate_admission(_mutated_manifest(manifest, mutate))


def test_traversal_promotion_fails_closed(manifest: dict) -> None:
    def mutate(clone: dict) -> None:
        clone["admitted"][0]["traversal_required"] = True

    with pytest.raises(native.NativeGroundingError):
        native.validate_admission(_mutated_manifest(manifest, mutate))


def test_support_promotion_fails_closed(manifest: dict) -> None:
    def mutate(clone: dict) -> None:
        clone["admitted"][0]["support"] = "runtime-queryable"

    with pytest.raises(native.NativeGroundingError):
        native.validate_admission(_mutated_manifest(manifest, mutate))


def test_missing_hard_gate_fails_closed(manifest: dict) -> None:
    def mutate(clone: dict) -> None:
        clone["excluded"] = [
            row for row in clone["excluded"] if row["identity"] != "allocatedTo"
        ]

    with pytest.raises(native.NativeGroundingError):
        native.validate_admission(_mutated_manifest(manifest, mutate))


def test_missing_reason_fails_closed(manifest: dict) -> None:
    def mutate(clone: dict) -> None:
        clone["excluded"][0]["reason"] = ""

    with pytest.raises(native.NativeGroundingError):
        native.validate_admission(_mutated_manifest(manifest, mutate))


def test_admitted_excluded_overlap_fails_closed(manifest: dict) -> None:
    def mutate(clone: dict) -> None:
        clone["excluded"].append({"identity": "VariationPoint", "reason": "overlap"})

    with pytest.raises(native.NativeGroundingError):
        native.validate_admission(_mutated_manifest(manifest, mutate))


def test_witness_mismatch_fails_closed(manifest: dict) -> None:
    def mutate(clone: dict) -> None:
        clone["admitted"][0]["witness"]["contains"] = "def NotARealConstruct {"

    with pytest.raises(native.NativeGroundingError):
        native.verify_witnesses(ROOT, _mutated_manifest(manifest, mutate))


def test_output_mismatch_fails_closed_directly() -> None:
    with pytest.raises(native.NativeGroundingError):
        native.validate_row_outputs(
            "VariationPoint",
            {
                "projection_row": True,  # must equal projection_required (false)
                "api_profile_entry": True,
                "traversal": False,
            },
        )
    with pytest.raises(native.NativeGroundingError):
        native.validate_row_outputs(
            "IncrementSize",
            {
                "projection_row": True,
                "api_profile_entry": False,
                "traversal": True,  # traversal must stay false
            },
        )
    with pytest.raises(native.NativeGroundingError):
        native.validate_row_outputs("NotAdmitted", {})


def test_generator_bug_cannot_silently_emit_projection_for_false_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A derive bug emitting projection rows for reviewed-false rows must be
    caught by the post-derivation validation before any artifact is built."""
    real_derive = native.derive_rows

    def corrupted_derive(root, manifest, source_revision):
        rows, entries = real_derive(root, manifest, source_revision)
        for row in rows:
            row["outputs"]["projection_row"] = True  # the hypothetical bug
        return rows, entries

    monkeypatch.setattr(native, "derive_rows", corrupted_derive)
    with pytest.raises(native.NativeGroundingError):
        native.build_artifact_pair(ROOT)


def test_generator_bug_cannot_silently_drop_profile_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_derive = native.derive_rows

    def corrupted_derive(root, manifest, source_revision):
        rows, _entries = real_derive(root, manifest, source_revision)
        return rows, []  # the hypothetical bug

    monkeypatch.setattr(native, "derive_rows", corrupted_derive)
    with pytest.raises(native.NativeGroundingError):
        native.build_artifact_pair(ROOT)
