"""Wave 0b adversarial tests: K inverse-pair parity (F5) and the structured
closure attestation.

Two matrices:

1. **Inverse-pair parity** — generation must fail when either ontology row of
   the K pair drifts, when the pair invariants break (swapped sides, opposite
   directions, one shared discriminator connection witness, identical
   strength), or when the verified companion identity no longer resolves.
2. **Closure attestation** — support promotion requires a structured,
   exact-revision ``ClosureAttestation``; every malformed, non-pass, stale, or
   foreign attestation fails closed, the bare boolean API is gone, and the
   projection/profile share one closure decision.
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

import de4sdv.semantic.projection as projection_module  # noqa: E402
from de4sdv.semantic.projection import (  # noqa: E402
    ClosureAttestation,
    RevisionIdentity,
    assert_profile_compatible,
    build_projection,
    build_representation_profile,
)

from test_semantic_projection_v0 import (  # noqa: E402
    REVISION,
    _attestation,
    _build,
    _build_profile,
    _by_id,
    _contract,
    _projection_binding_index,
)

PROJECTION = projection_module
CANONICAL = "derivesRequirementFromNeed"
COMPANION = "derivedRequirementsOfNeed"
K_GIT_SHA = "72926c958d2bd3b1001088fa657ec906dffd53e7"
K_PROJECT = "ea96301d-343a-4592-bad4-5dd997ca906a"
K_COMMIT = "82ef02df-94fe-4100-94c9-2f961f314a28"

R6_RECORD = json.loads(
    (ROOT / "docs/method-conformance/o1/closure-evidence.json").read_text(
        encoding="utf-8"
    )
)["records"][0]


def _pair_fields(row: str = COMPANION) -> dict:
    contract = _contract()
    canonical, companion = PROJECTION._pair_oracle_rows(contract)
    return canonical if row == CANONICAL else companion


def _tamper(field: str, value, row: str = COMPANION):
    """Return a contract with one oracle field of one pair row mutated."""
    contract = _contract()
    if field in ("domain", "range"):
        contract.relationships[row][field] = value
    else:
        contract.relationships[row]["sysml_mapping"][field] = value
    return contract


def _build_with(contract, **kwargs) -> dict:
    return build_projection(
        contract,
        _projection_binding_index(),
        REVISION,
        _by_id(),
        repository_root=ROOT,
        **kwargs,
    )


def _expect_pair_drift(contract, field_hint: str, **kwargs) -> None:
    with pytest.raises(ValueError, match="parity oracle drift") as excinfo:
        _build_with(contract, **kwargs)
    assert field_hint in str(excinfo.value), str(excinfo.value)


# ---------------------------------------------------------------------------
# 1. Inverse-pair parity (F5): companion-row drift matrix
# ---------------------------------------------------------------------------


COMPANION_DRIFTS = [
    ("domain", "Requirement"),
    ("range", "Need"),
    ("strategy", "dependency"),
    ("connection_definition", "SomeOtherDefinition"),
    ("need_role", "someOtherNeedRole"),
    ("requirement_role", "someOtherRequirementRole"),
    ("query_direction", "inverse"),
    ("source_lineage_of", "Requirement"),
    ("target_lineage_of", "Need"),
    ("semantic_strength", "allocation"),
]


@pytest.mark.parametrize("field, value", COMPANION_DRIFTS)
def test_companion_row_drift_fails_generation(field: str, value) -> None:
    """Mutating ONLY the companion row (any field) fails generation."""
    _expect_pair_drift(_tamper(field, value), f"{COMPANION}.{field}")


CANONICAL_DRIFTS = [
    ("domain", "Need"),
    ("range", "Requirement"),
    ("strategy", "dependency"),
    ("connection_definition", "SomeOtherDefinition"),
    ("need_role", "someOtherNeedRole"),
    ("requirement_role", "someOtherRequirementRole"),
    ("source_lineage_of", "Need"),
    ("target_lineage_of", "Requirement"),
    ("semantic_strength", "allocation"),
]


@pytest.mark.parametrize("field, value", CANONICAL_DRIFTS)
def test_canonical_row_drift_fails_generation(field: str, value) -> None:
    """Mutating ONLY the canonical row (any field) fails generation."""
    _expect_pair_drift(_tamper(field, value, row=CANONICAL), f"{CANONICAL}.{field}")


def test_pair_directions_must_stay_opposite() -> None:
    # Companion flipped to the canonical direction: no longer a pair.
    _expect_pair_drift(
        _tamper("query_direction", "inverse", row=COMPANION),
        "query_direction",
    )
    # Canonical flipped alone: the companion's expected direction flips too.
    _expect_pair_drift(
        _tamper("query_direction", "forward", row=CANONICAL),
        "query_direction",
    )


def test_unsupported_pair_direction_fails_closed() -> None:
    # A canonical direction outside the pair vocabulary cannot define a pair.
    with pytest.raises(ValueError, match="unsupported K query direction"):
        _build_with(_tamper("query_direction", "sideways", row=CANONICAL))
    # A companion direction outside the vocabulary is a plain pair drift.
    _expect_pair_drift(
        _tamper("query_direction", "sideways", row=COMPANION),
        "query_direction",
    )


def test_pair_must_swap_domain_range() -> None:
    """A pair that stops swapping domain/range fails, even if each value is
    individually plausible."""
    contract = _tamper("domain", "Requirement")  # companion domain = canonical
    contract.relationships[COMPANION]["range"] = "Need"
    _expect_pair_drift(contract, "pair.domain/range")


def test_pair_must_use_same_discriminator_definition() -> None:
    """A companion pointing at a different connection definition would be a
    second modeled fact: fail closed (no second witness may be synthesized)."""
    _expect_pair_drift(
        _tamper("connection_definition", "AnotherConnectionDefinition"),
        "pair.connection_definition",
    )


def test_pair_lineage_sides_must_swap() -> None:
    contract = _tamper("source_lineage_of", "Requirement")
    contract.relationships[COMPANION]["sysml_mapping"]["target_lineage_of"] = "Need"
    _expect_pair_drift(contract, "pair.lineage")


def test_pair_strength_must_match() -> None:
    _expect_pair_drift(
        _tamper("semantic_strength", "satisfaction"), "semantic_strength"
    )


def test_inverse_navigation_identity_mismatch_fails() -> None:
    """The companion identity is parity-verified, not a loose literal."""
    contract = _contract()
    # Renaming the companion row leaves no resolvable inverse identity.
    contract.relationships["renamedCompanion"] = contract.relationships.pop(
        COMPANION
    )
    with pytest.raises(KeyError):
        _build_with(contract)
    # A changed module-level expected identity is equally unresolvable.
    import unittest.mock as mock

    with mock.patch.object(PROJECTION, "_INVERSE_PREDICATE", "renamedCompanion"):
        with pytest.raises(KeyError):
            _build_with(_contract())
    # With the real contract the verified identity is the companion.
    projection = _build()
    assert projection["predicate"]["inverse_navigation_identity"] == COMPANION


def test_kernel_end_declaration_drift_fails_generation() -> None:
    """The shared kernel end-type declarations are part of the oracle pair."""
    contract = _contract()
    contract.classes["Need"]["kernel"]["declaration"] = "requirement def SomeOtherNeed"
    _expect_pair_drift(contract, "need_end_type_declaration")
    contract = _contract()
    contract.classes["Requirement"]["kernel"]["declaration"] = (
        "requirement def SomeOtherRequirement"
    )
    _expect_pair_drift(contract, "requirement_end_type_declaration")


def test_pair_resolves_to_one_witness_and_the_accepted_values() -> None:
    canonical = _pair_fields(CANONICAL)
    companion = _pair_fields(COMPANION)
    # One shared discriminator: both rows resolve to the single application
    # connection definition (no second modeled fact).
    assert canonical["connection_definition"] == "DerivesFromNeed"
    assert companion["connection_definition"] == "DerivesFromNeed"
    # Same typed model roles; identical strength.
    assert canonical["need_role"] == companion["need_role"] == "need"
    assert (
        canonical["requirement_role"]
        == companion["requirement_role"]
        == "derivedRequirement"
    )
    assert canonical["semantic_strength"] == companion["semantic_strength"] == "derivation"
    # Swapped sides.
    assert canonical["domain"] == "Requirement"
    assert canonical["range"] == "Need"
    assert companion["domain"] == canonical["range"]
    assert companion["range"] == canonical["domain"]
    assert companion["source_lineage_of"] == canonical["target_lineage_of"]
    assert companion["target_lineage_of"] == canonical["source_lineage_of"]
    # Opposite directions: the accepted pair values.
    assert canonical["query_direction"] == "inverse"
    assert companion["query_direction"] == "forward"
    # The canonical row carries the swap check against the companion.
    assert canonical["strategy"] == companion["strategy"] == "derivation-connection"
    # The generated projection still carries exactly one predicate row.
    projection = _build()
    assert projection["predicate"]["identity"] == CANONICAL
    assert projection["predicate"]["inverse_navigation_identity"] == COMPANION


# ---------------------------------------------------------------------------
# 2. Closure attestation matrix
# ---------------------------------------------------------------------------


def test_no_attestation_stays_vocabulary_only() -> None:
    assert _build()["predicate"]["support_state"] == "vocabulary-only"


def test_valid_attestation_promotes_to_supported() -> None:
    assert (
        _build(closure_attestation=_attestation())["predicate"]["support_state"]
        == "supported"
    )


CLOSURE_REJECTIONS = [
    ({"git_commit": "1" * 40}, "stale or foreign"),
    ({"git_commit": "not-a-sha"}, "40-hex"),
    ({"sysml_project_id": "some-other-project"}, "sysml_project_id"),
    ({"sysml_commit_id": "some-other-commit"}, "sysml_commit_id"),
    ({"proof_result": "fail"}, "not a passing proof"),
    ({"proof_result": "indeterminate"}, "not a passing proof"),
    ({"proof_result": ""}, "not a passing proof"),
    (
        {"subject_identities": ("DerivesFromNeed", "derivesRequirementFromNeed")},
        "required semantic subjects",
    ),
    (
        {"subject_identities": ("derivesRequirementFromNeed", "derivedRequirementsOfNeed")},
        "required semantic subjects",
    ),
    (
        {"subject_identities": ("DerivesFromNeed", "derivedRequirementsOfNeed")},
        "required semantic subjects",
    ),
    ({"subject_identities": ()}, "required semantic subjects"),
    ({"evidence_id": "   "}, "evidence_id"),
    ({"artifact_identity": ""}, "artifact_identity"),
    ({"artifact_digest": "not-a-digest"}, "artifact_digest"),
    ({"artifact_digest": "sha256:not-hex"}, "artifact_digest"),
]


@pytest.mark.parametrize("overrides, message", CLOSURE_REJECTIONS)
def test_closure_attestation_mismatch_fails_closed(overrides, message) -> None:
    with pytest.raises(ValueError, match=message):
        _build(closure_attestation=_attestation(**overrides))


def test_closure_attestation_digest_is_optional() -> None:
    """A digest is taken where available; absence is not malformed."""
    assert (
        _build(closure_attestation=_attestation(artifact_digest=None))["predicate"][
            "support_state"
        ]
        == "supported"
    )


def test_bare_boolean_is_not_a_valid_attestation() -> None:
    with pytest.raises(ValueError, match="ClosureAttestation or a mapping"):
        _build(closure_attestation=True)
    with pytest.raises(ValueError, match="ClosureAttestation or a mapping"):
        _build(closure_attestation="pass")


def test_malformed_mapping_is_rejected() -> None:
    with pytest.raises(ValueError, match="missing fields"):
        _build(closure_attestation={"evidence_id": "only-an-id"})
    with pytest.raises(ValueError, match="subject_identities"):
        _build(
            closure_attestation={
                "evidence_id": "x",
                "git_commit": REVISION.git_commit,
                "sysml_project_id": REVISION.sysml_project_id,
                "sysml_commit_id": REVISION.sysml_commit_id,
                "proof_result": "pass",
                "subject_identities": "DerivesFromNeed",
                "artifact_identity": "y",
            }
        )


def test_boolean_promotion_api_is_removed() -> None:
    """No builder accepts the removed boolean; only the attestation path."""
    for builder in (build_projection, build_representation_profile):
        parameters = inspect.signature(builder).parameters
        assert "witness_closure_verified" not in parameters
        assert "closure_attestation" in parameters
    with pytest.raises(TypeError):
        _build(witness_closure_verified=True)
    with pytest.raises(TypeError):
        _build_profile(witness_closure_verified=True)


def test_no_active_caller_relies_on_the_removed_boolean() -> None:
    """No active code depends on the removed boolean. The two removal-proof
    test files are the only places allowed to name it (they prove the
    TypeError on use); everything else must be clean."""
    removal_proofs = {
        "tests/test_k_inverse_parity_and_closure.py",
        "tests/test_semantic_projection_v0.py",
    }
    hits: list[str] = []
    for tree in ("de4sdv", "scripts", "tests", "tools"):
        for path in sorted((ROOT / tree).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            relative = str(path.relative_to(ROOT))
            if relative in removal_proofs:
                continue
            if "witness_closure_verified" in path.read_text(encoding="utf-8"):
                hits.append(relative)
    assert hits == []
    # And within the removal proofs the name only appears as a kwarg use that
    # must raise TypeError (never as a working parameter).
    for relative in removal_proofs:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "witness_closure_verified=True" in text


# ---------------------------------------------------------------------------
# 3. Retained R6 #3 evidence: expressible, exact-revision only
# ---------------------------------------------------------------------------


def _r6_attestation() -> ClosureAttestation:
    """The retained R6 #3 closure record as a structured attestation.

    The digest mapped in is the GitHub ARCHIVE digest of the retained
    ingestion artifact — not an internal export/binding/semantic digest
    (which remains explicitly unrecorded and is never fabricated).
    """
    record = R6_RECORD
    return ClosureAttestation.from_mapping(
        {
            "evidence_id": record["id"],
            "git_commit": record["git_sha"],
            "sysml_project_id": record["sysml_project_id"],
            "sysml_commit_id": record["sysml_commit_id"],
            "proof_result": record["proof"]["result"],
            "subject_identities": record["subject_identities"],
            "artifact_identity": record["artifact"]["name"],
            "artifact_digest": record["artifact"]["archive_content_digest"],
        }
    )


def test_r6_3_evidence_promotes_only_its_exact_revision() -> None:
    r6_revision = RevisionIdentity(
        git_commit=K_GIT_SHA, sysml_project_id=K_PROJECT, sysml_commit_id=K_COMMIT
    )
    projection = build_projection(
        _contract(),
        _projection_binding_index(),
        r6_revision,
        _by_id(),
        repository_root=ROOT,
        closure_attestation=_r6_attestation(),
    )
    assert projection["predicate"]["support_state"] == "supported"
    assert projection["revision_binding"]["git_commit"] == K_GIT_SHA
    # The same historical attestation must NOT promote another revision
    # (no automatic revision-equivalence mechanism exists in Wave 0b).
    with pytest.raises(ValueError, match="stale or foreign"):
        _build(closure_attestation=_r6_attestation())


def test_r6_3_attestation_rejects_each_revision_field_mismatch() -> None:
    r6 = _r6_attestation()
    for replacement, message in (
        (
            RevisionIdentity(
                git_commit="3" * 40,
                sysml_project_id=K_PROJECT,
                sysml_commit_id=K_COMMIT,
            ),
            "stale or foreign",
        ),
        (
            RevisionIdentity(
                git_commit=K_GIT_SHA,
                sysml_project_id="other-project",
                sysml_commit_id=K_COMMIT,
            ),
            "sysml_project_id",
        ),
        (
            RevisionIdentity(
                git_commit=K_GIT_SHA,
                sysml_project_id=K_PROJECT,
                sysml_commit_id="other-commit",
            ),
            "sysml_commit_id",
        ),
    ):
        with pytest.raises(ValueError, match=message):
            build_projection(
                _contract(),
                _projection_binding_index(),
                replacement,
                _by_id(),
                repository_root=ROOT,
                closure_attestation=r6,
            )


# ---------------------------------------------------------------------------
# 4. Projection/profile agreement on closure/support state
# ---------------------------------------------------------------------------


def test_projection_and_profile_agree_on_closure_state() -> None:
    attestation = _attestation()
    projection = _build(closure_attestation=attestation)
    profile = _build_profile(closure_attestation=attestation)
    assert projection["predicate"]["support_state"] == "supported"
    assert (
        profile["predicate_echo"]["support_state_from_projection"] == "supported"
    )
    assert profile["model_revision_binding"] == projection["revision_binding"]
    # And without an attestation both stay honest.
    assert _build()["predicate"]["support_state"] == "vocabulary-only"
    assert (
        _build_profile()["predicate_echo"]["support_state_from_projection"]
        == "vocabulary-only"
    )


def test_projection_and_profile_fail_identically_on_stale_attestation() -> None:
    stale = _attestation(git_commit="2" * 40)
    with pytest.raises(ValueError, match="stale or foreign"):
        _build(closure_attestation=stale)
    with pytest.raises(ValueError, match="stale or foreign"):
        _build_profile(closure_attestation=stale)


def test_profile_support_echo_cannot_leave_the_honest_vocabulary() -> None:
    profile = _build_profile()
    mutated = json.loads(json.dumps(profile))
    mutated["predicate_echo"]["support_state_from_projection"] = "proven"
    with pytest.raises(ValueError, match="honest support-state vocabulary"):
        assert_profile_compatible(mutated)