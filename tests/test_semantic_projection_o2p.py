"""Machine locks for the O2+ native/library grounding & projection layer.

The layer is governed by review Deliverable 8 wave 3 (native/library
projection rows over already-native constructs) and the O4 execution
register rows for the admitted identities. These tests lock:

* the admitted set is EXACTLY the reviewed safe subset (eight identities)
  with per-row flags equal to the reviewed values;
* the excluded set carries a reason for every considered-but-not-admitted
  row and contains the hard gates that must never be admitted;
* no frozen O2 (v1/v1.1/v1.2 thirteen) and no frozen O3 identity is
  admitted or emitted;
* generation is deterministic and read-only; the committed pair equals
  regeneration from the recorded source revision;
* support stays vocabulary-only, traversal is false everywhere, and no
  support promotion can slip through the generation path.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic import projection_o2p as po2p
from de4sdv.semantic.authority_inventory import validate_source_binding

ROOT = Path(__file__).resolve().parents[1]

# Permanent safe-set 2 squash (#298, M6); Rebind 4 preserves its semantics.
# Definition admission batch 1 (amended): the O2+ pair was regenerated on
# this PR's source commit A1 (bound to the chain sources).
COMMITTED_SOURCE_REVISION = "f64620cb958888ea8a749bfd16945fc7c1371a33"

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
    return po2p.load_admission_o2p(ROOT / po2p.ADMISSION_O2P_PATH)


@pytest.fixture(scope="module")
def artifacts() -> dict:
    projection = json.loads(
        (ROOT / po2p.PROJECTION_O2P_PATH).read_text(encoding="utf-8")
    )
    profile = json.loads((ROOT / po2p.PROFILE_O2P_PATH).read_text(encoding="utf-8"))
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


def test_frozen_o2_surface_is_never_admitted(manifest: dict) -> None:
    admitted = {row["identity"] for row in manifest["admitted"]}
    assert admitted & set(po2p.FROZEN_O2_IDENTITIES) == set()
    # The frozen list itself must equal the actual committed v1/v1.1/v1.2 rows.
    actual: list[str] = []
    for name in ("semantic-projection-v1.json", "semantic-projection-v1.1.json", "semantic-projection-v1.2.json"):
        document = json.loads(
            (ROOT / "docs/method-conformance/o2" / name).read_text(encoding="utf-8")
        )
        actual.extend(r["identity"] for r in document.get("concepts", []))
        actual.extend(r["identity"] for r in document.get("predicates", []))
    assert sorted(actual) == sorted(po2p.FROZEN_O2_IDENTITIES)


def test_frozen_o3_surface_is_never_admitted(manifest: dict) -> None:
    from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES

    admitted = {row["identity"] for row in manifest["admitted"]}
    assert admitted & set(MIGRATED_IDENTITIES) == set()
    assert len(MIGRATED_IDENTITIES) == 13


def test_witnesses_exist_in_the_model() -> None:
    manifest = po2p.load_admission_o2p(ROOT / po2p.ADMISSION_O2P_PATH)
    po2p.verify_witnesses(ROOT, manifest)  # raises on any missing construct


def test_projection_rows_are_exactly_the_admitted_set(artifacts: dict) -> None:
    rows = artifacts["projection"]["rows"]
    assert [r["identity"] for r in rows] == [
        row["identity"] for row in po2p.load_admission_o2p(
            ROOT / po2p.ADMISSION_O2P_PATH
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
    from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES

    emitted = {row["identity"] for row in artifacts["projection"]["rows"]}
    assert emitted & set(po2p.FROZEN_O2_IDENTITIES) == set()
    assert emitted & set(MIGRATED_IDENTITIES) == set()


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


def test_pair_is_bound_to_the_committed_source_revision(artifacts: dict) -> None:
    for document in (artifacts["projection"], artifacts["profile"]):
        assert document["binding"]["source_revision"] == COMMITTED_SOURCE_REVISION
        assert validate_source_binding(ROOT, document["binding"]) == []


def test_regeneration_is_deterministic() -> None:
    revision = json.loads(
        (ROOT / po2p.PROJECTION_O2P_PATH).read_text(encoding="utf-8")
    )["binding"]["source_revision"]
    first = po2p.build_pair_o2p(ROOT, source_revision=revision)
    second = po2p.build_pair_o2p(ROOT, source_revision=revision)
    assert po2p.canonical_json(first["projection"]) == po2p.canonical_json(
        second["projection"]
    )
    assert po2p.canonical_json(first["profile"]) == po2p.canonical_json(
        second["profile"]
    )


def test_check_passes_on_the_committed_tree() -> None:
    assert po2p.run_check_errors_o2p(ROOT) == []


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
    binding = artifacts["projection"]["binding"]
    witness_files = sorted(
        {
            row["witness"]["file"]
            for row in po2p.load_admission_o2p(
                ROOT / po2p.ADMISSION_O2P_PATH
            )["admitted"]
        }
    )
    assert binding["semantic_model_revision"]["model_inputs"] == witness_files
    assert po2p.SYSIDE_WORKFLOW_PATH not in binding["semantic_model_revision"][
        "model_inputs"
    ]
    # Still revision-bound for reproducibility...
    assert binding["tooling_revision"]["tooling_inputs"] == [
        po2p.SYSIDE_WORKFLOW_PATH
    ]
    assert po2p.SYSIDE_WORKFLOW_PATH in binding["bound_inputs"]
    # ...but classified as tooling, never as a semantic-model input.
    for path in binding["semantic_model_revision"]["model_inputs"]:
        assert path.endswith(".sysml")


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

    with pytest.raises(po2p.ProjectionO2PError):
        po2p.validate_admission_o2p(_mutated_manifest(manifest, mutate))


def test_traversal_promotion_fails_closed(manifest: dict) -> None:
    def mutate(clone: dict) -> None:
        clone["admitted"][0]["traversal_required"] = True

    with pytest.raises(po2p.ProjectionO2PError):
        po2p.validate_admission_o2p(_mutated_manifest(manifest, mutate))


def test_support_promotion_fails_closed(manifest: dict) -> None:
    def mutate(clone: dict) -> None:
        clone["admitted"][0]["support"] = "runtime-queryable"

    with pytest.raises(po2p.ProjectionO2PError):
        po2p.validate_admission_o2p(_mutated_manifest(manifest, mutate))


def test_missing_hard_gate_fails_closed(manifest: dict) -> None:
    def mutate(clone: dict) -> None:
        clone["excluded"] = [
            row for row in clone["excluded"] if row["identity"] != "allocatedTo"
        ]

    with pytest.raises(po2p.ProjectionO2PError):
        po2p.validate_admission_o2p(_mutated_manifest(manifest, mutate))


def test_missing_reason_fails_closed(manifest: dict) -> None:
    def mutate(clone: dict) -> None:
        clone["excluded"][0]["reason"] = ""

    with pytest.raises(po2p.ProjectionO2PError):
        po2p.validate_admission_o2p(_mutated_manifest(manifest, mutate))


def test_admitted_excluded_overlap_fails_closed(manifest: dict) -> None:
    def mutate(clone: dict) -> None:
        clone["excluded"].append({"identity": "VariationPoint", "reason": "overlap"})

    with pytest.raises(po2p.ProjectionO2PError):
        po2p.validate_admission_o2p(_mutated_manifest(manifest, mutate))


def test_witness_mismatch_fails_closed(manifest: dict) -> None:
    def mutate(clone: dict) -> None:
        clone["admitted"][0]["witness"]["contains"] = "def NotARealConstruct {"

    with pytest.raises(po2p.ProjectionO2PError):
        po2p.verify_witnesses(ROOT, _mutated_manifest(manifest, mutate))


def test_output_mismatch_fails_closed_directly() -> None:
    with pytest.raises(po2p.ProjectionO2PError):
        po2p.validate_row_outputs_o2p(
            "VariationPoint",
            {
                "projection_row": True,  # must equal projection_required (false)
                "api_profile_entry": True,
                "traversal": False,
            },
        )
    with pytest.raises(po2p.ProjectionO2PError):
        po2p.validate_row_outputs_o2p(
            "IncrementSize",
            {
                "projection_row": True,
                "api_profile_entry": False,
                "traversal": True,  # traversal must stay false
            },
        )
    with pytest.raises(po2p.ProjectionO2PError):
        po2p.validate_row_outputs_o2p("NotAdmitted", {})


def test_generator_bug_cannot_silently_emit_projection_for_false_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A derive bug emitting projection rows for reviewed-false rows must be
    caught by the post-derivation validation before any artifact is built."""
    revision = json.loads(
        (ROOT / po2p.PROJECTION_O2P_PATH).read_text(encoding="utf-8")
    )["binding"]["source_revision"]
    real_derive = po2p.derive_rows_o2p

    def corrupted_derive(root, manifest, source_revision):
        rows, entries = real_derive(root, manifest, source_revision)
        for row in rows:
            row["outputs"]["projection_row"] = True  # the hypothetical bug
        return rows, entries

    monkeypatch.setattr(po2p, "derive_rows_o2p", corrupted_derive)
    with pytest.raises(po2p.ProjectionO2PError):
        po2p.build_pair_o2p(ROOT, source_revision=revision)


def test_generator_bug_cannot_silently_drop_profile_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision = json.loads(
        (ROOT / po2p.PROJECTION_O2P_PATH).read_text(encoding="utf-8")
    )["binding"]["source_revision"]
    real_derive = po2p.derive_rows_o2p

    def corrupted_derive(root, manifest, source_revision):
        rows, _entries = real_derive(root, manifest, source_revision)
        return rows, []  # the hypothetical bug

    monkeypatch.setattr(po2p, "derive_rows_o2p", corrupted_derive)
    with pytest.raises(po2p.ProjectionO2PError):
        po2p.build_pair_o2p(ROOT, source_revision=revision)
