"""External evidence-reference contract: fail-closed validation, no claim inflation."""
import copy
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _reference(**overrides):
    record = {
        "case_identity": "VC-MW-010",
        "artifact_identity": "retained://middleware/run-2026-09-19T21-00Z",
        "artifact_revision": "rev-7",
        "digest": "A" * 64,
        "run": "run-34630102233",
        "tested_scope": ["INC-MW-010", "bench/mw-e014"],
    }
    record.update(overrides)
    return record


def _manifest(**overrides):
    manifest = {
        "baseline_identity": "baseline://mw-010/phase-12",
        "manifest_digest": {"algorithm": "sha256", "value": "b" * 64},
        "entries": ["retained://middleware/run-2026-09-19T21-00Z@rev-7"],
    }
    manifest.update(overrides)
    return manifest


# --------------------------------------------------------------------------- #
# Typed reference schema
# --------------------------------------------------------------------------- #

def test_valid_reference_normalizes_and_never_implies_pass():
    from de4sdv.semantic.external_reference_contract import validate_typed_reference

    normalized = validate_typed_reference(_reference())
    assert normalized["digest"] == {"algorithm": "sha256", "value": "a" * 64}
    assert normalized["case_identity"] == "VC-MW-010"
    assert normalized["artifact_revision"] == "rev-7"
    assert normalized["version_identity"] == (
        "retained://middleware/run-2026-09-19T21-00Z@rev-7"
    )
    assert normalized["tested_scope"] == sorted(["INC-MW-010", "bench/mw-e014"])
    assert normalized["implies_pass"] is False
    assert normalized["implies_verification"] is False
    assert normalized["implies_acceptance"] is False
    assert normalized["traversal"] is False
    assert normalized["runtime_support"] == "external"
    assert normalized["content_mirrored"] is False


def test_evidence_reference_name_is_the_same_single_contract():
    from de4sdv.semantic.external_reference_contract import (
        validate_evidence_reference,
        validate_typed_reference,
    )

    assert validate_evidence_reference(_reference()) == validate_typed_reference(_reference())


def test_missing_or_malformed_fields_fail_closed():
    from de4sdv.semantic.external_reference_contract import (
        EvidenceReferenceError,
        validate_typed_reference,
    )

    for record in (
        _reference(case_identity=""),
        _reference(artifact_identity=""),
        _reference(artifact_revision=""),
        _reference(digest="not-a-digest"),
        _reference(digest={"algorithm": "sha1", "value": "c" * 40}),
        _reference(run=""),
        _reference(tested_scope=[]),
        _reference(tested_scope=["ok", 7]),
        {},
    ):
        with pytest.raises(EvidenceReferenceError):
            validate_typed_reference(record)


def test_claim_inflating_or_traversal_fields_are_refused():
    from de4sdv.semantic.external_reference_contract import (
        EvidenceReferenceError,
        validate_typed_reference,
    )

    for field in ("verdict", "passed", "accepted", "approval", "status", "traversal",
                  "sysml_mapping", "implies_pass", "implies_acceptance", "implies_approval"):
        with pytest.raises(EvidenceReferenceError, match="claim-inflating"):
            validate_typed_reference(_reference(**{field: True}))


# --------------------------------------------------------------------------- #
# Baseline membership (capturedInBaseline)
# --------------------------------------------------------------------------- #

def test_baseline_inclusion_is_exact_and_never_approves():
    from de4sdv.semantic.external_reference_contract import baseline_inclusion

    result = baseline_inclusion(_reference(), _manifest())
    assert result["included"] is True
    assert result["version_identity"].endswith("@rev-7")
    assert result["implies_approval"] is False
    assert result["implies_pass"] is False
    assert result["implies_acceptance"] is False
    assert result["traversal"] is False


def test_other_revision_is_not_included_and_still_no_claim():
    from de4sdv.semantic.external_reference_contract import baseline_inclusion

    result = baseline_inclusion(_reference(artifact_revision="rev-8"), _manifest())
    assert result["included"] is False
    assert result["implies_approval"] is False
    result = baseline_inclusion(_reference(artifact_identity="retained://other"), _manifest())
    assert result["included"] is False
    assert result["implies_approval"] is False


def test_baseline_manifest_requires_identity_and_entries():
    from de4sdv.semantic.external_reference_contract import (
        EvidenceReferenceError,
        validate_baseline_manifest,
    )

    with pytest.raises(EvidenceReferenceError):
        validate_baseline_manifest(_manifest(baseline_identity=""))
    with pytest.raises(EvidenceReferenceError):
        validate_baseline_manifest(_manifest(entries=[]))
    with pytest.raises(EvidenceReferenceError):
        validate_baseline_manifest(_manifest(manifest_digest="b" * 63))
    with pytest.raises(EvidenceReferenceError, match="claim-inflating"):
        validate_baseline_manifest(_manifest(approval=True))
    normalized = validate_baseline_manifest(_manifest())
    assert normalized["second_baseline_list"] is False
    assert normalized["version_identity_form"] == "<artifact_identity>@<artifact_revision>"


# --------------------------------------------------------------------------- #
# Association / blocked-state surface
# --------------------------------------------------------------------------- #

def test_association_state_contains_no_verdict_fields():
    from de4sdv.semantic.external_reference_contract import association_state

    state = association_state(_reference())
    assert state["external_reference_validated"] is True
    assert state["implies_pass"] is False
    assert state["implies_acceptance"] is False
    assert state["traversal"] is False
    assert state["runtime_support"] == "external"
    forbidden = {"verdict", "passed", "accepted", "approval", "status"}
    assert not (forbidden & set(state))


def test_blocked_state_is_surfaced_for_queries():
    from de4sdv.semantic.external_reference_contract import (
        EvidenceReferenceError,
        external_boundary_state,
    )

    state = external_boundary_state("hasEvidence")
    assert state["identity"] == "hasEvidence"
    assert state["runtime_support"] == "external"
    assert state["traversal"] is False
    assert state["external_facts_retained"] is True
    assert state["blocked_reason"]
    assert state["implies_pass"] is False
    with pytest.raises(EvidenceReferenceError):
        external_boundary_state("")


# --------------------------------------------------------------------------- #
# Prepared profile artifact: family lock + profile entries
# --------------------------------------------------------------------------- #

def _load():
    from de4sdv.semantic import external_reference_contract as module

    document = module.load_profile(REPO_ROOT / module.PROFILE_PATH)
    register = module.load_register(REPO_ROOT)
    review = module.load_review(REPO_ROOT)
    return module, document, register, review


def test_committed_profile_family_is_derived_and_traversal_free():
    module, document, register, review = _load()

    outputs = module.validate_profile(REPO_ROOT, document, register, review)
    assert outputs["family"] == [
        "Baseline",
        "EvidenceArtifact",
        "capturedInBaseline",
        "hasEvidence",
    ]
    assert set(outputs["scope_rows"]) == {
        "EvidenceArtifact",
        "hasEvidence",
        "capturedInBaseline",
    }
    assert set(outputs["scope_rows"]) < set(outputs["family"])
    for row in outputs["profile_rows"]:
        assert row["traversal"] is False
        assert row["runtime_support"] == "external"
        assert row["implies_pass"] is False
        assert row["implies_acceptance"] is False
        assert row["definition"]
        assert row["mechanics"]
    baseline = next(r for r in outputs["profile_rows"] if r["identity"] == "Baseline")
    assert baseline["representation_class"] == "model-resident-boundary-identity"
    assert baseline["declaration"]["name"] == "DE4SDVEvidenceBaseline"


def test_profile_family_drift_fails_closed():
    module, document, register, review = _load()

    drifted = copy.deepcopy(document)
    drifted["expected_rows"] = ["EvidenceArtifact", "hasEvidence", "capturedInBaseline"]
    with pytest.raises(module.EvidenceReferenceError, match="family drift"):
        module.validate_profile(REPO_ROOT, drifted, register, review)

    extra = copy.deepcopy(document)
    extra["expected_rows"] = document["expected_rows"] + ["Foreign"]
    with pytest.raises(module.EvidenceReferenceError, match="family drift"):
        module.validate_profile(REPO_ROOT, extra, register, review)

    scope_drift = copy.deepcopy(document)
    scope_drift["scope_rows"] = document["scope_rows"] + ["Foreign"]
    with pytest.raises(module.EvidenceReferenceError, match="outside the derived family"):
        module.validate_profile(REPO_ROOT, scope_drift, register, review)


def test_profile_schema_block_is_machine_locked():
    module, document, register, review = _load()

    unlocked = copy.deepcopy(document)
    unlocked["typed_reference_schema"]["machine_locked"]["traversal"] = True
    with pytest.raises(module.EvidenceReferenceError, match="machine_locked.traversal"):
        module.validate_profile(REPO_ROOT, unlocked, register, review)

    weakened = copy.deepcopy(document)
    weakened["typed_reference_schema"]["forbidden_record_fields"] = ["verdict"]
    with pytest.raises(module.EvidenceReferenceError, match="forbidden_record_fields"):
        module.validate_profile(REPO_ROOT, weakened, register, review)

    renamed = copy.deepcopy(document)
    renamed["typed_reference_schema"]["required_fields"].pop("artifact_revision")
    with pytest.raises(module.EvidenceReferenceError, match="required_fields"):
        module.validate_profile(REPO_ROOT, renamed, register, review)

    active = copy.deepcopy(document)
    active["activation"] = "traversal"
    with pytest.raises(module.EvidenceReferenceError, match="prepared"):
        module.validate_profile(REPO_ROOT, active, register, review)


def test_profile_entries_refuse_claim_inflation_and_foreign_rows():
    module, document, register, review = _load()

    inflated = copy.deepcopy(document)
    inflated["profile_entries"][0]["traversal"] = False
    with pytest.raises(module.EvidenceReferenceError, match="unknown keys"):
        module.validate_profile(REPO_ROOT, inflated, register, review)

    foreign = copy.deepcopy(document)
    foreign["profile_entries"].append(
        {"identity": "Foreign", "representation_class": "external-reference-record",
         "mechanics": "x", "declaration": None}
    )
    with pytest.raises(module.EvidenceReferenceError, match="outside the derived family"):
        module.validate_profile(REPO_ROOT, foreign, register, review)

    undeclared = copy.deepcopy(document)
    baseline = next(e for e in undeclared["profile_entries"] if e["identity"] == "Baseline")
    baseline["declaration"] = {"file": "textual-notation-of-model/missing.sysml",
                               "name": "DE4SDVEvidenceBaseline"}
    with pytest.raises(module.EvidenceReferenceError, match="declaration file missing"):
        module.validate_profile(REPO_ROOT, undeclared, register, review)

    missing_entry = copy.deepcopy(document)
    missing_entry["profile_entries"] = [
        e for e in missing_entry["profile_entries"] if e["identity"] != "hasEvidence"
    ]
    with pytest.raises(module.EvidenceReferenceError, match="without a profile entry"):
        module.validate_profile(REPO_ROOT, missing_entry, register, review)


def test_profile_refuses_reviewed_disposition_or_flag_changes():
    module, document, register, review = _load()

    for mutate in (
        lambda row: row["target"].__setitem__("disposition", "REDESIGN"),
        lambda row: row["target"].__setitem__("traversal_required", True),
        lambda row: row["target"].__setitem__("api_profile_required", True),
        lambda row: row["target"].__setitem__("projection_required", True),
        lambda row: row["target"].__setitem__("runtime_support_target", "runtime-queryable"),
    ):
        edited = copy.deepcopy(review)
        for row in edited["rows"]:
            if row.get("identity") == "hasEvidence":
                mutate(row)
        with pytest.raises(module.EvidenceReferenceError):
            module.validate_profile(REPO_ROOT, document, register, edited)


def test_profile_run_check_errors_is_fail_closed(tmp_path):
    module, _, _, _ = _load()

    assert module.run_check_errors(REPO_ROOT) == []
    empty = tmp_path / "empty"
    empty.mkdir()
    errors = module.run_check_errors(empty)
    assert errors and module.PROFILE_PATH in errors[0]


def test_contract_never_fetches_content_and_stays_read_only():
    import inspect

    from de4sdv.semantic import external_reference_contract as module

    source = inspect.getsource(module)
    for banned in ("requests", "urllib", "http", "subprocess", "open("):
        assert banned not in source, f"contract must stay offline/read-only: {banned}"
