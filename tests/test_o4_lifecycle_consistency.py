"""O4 lifecycle-consistency invariant tests: O3 stays frozen throughout O4.

The invariant (``scripts/check_o4_lifecycle_consistency.py``, wired into
``check_repo.py``) is precisely scoped to the **77 retained O4-target
identities** derived from the generated execution register
(``membership == "o4-target"``). It forbids future O3 authority-transition/
admission obligations for those targets — in the O1 reviewed decisions
(``required_evidence``), the accepted O4 review (``target.evidence_needed``,
``dependencies``), and the register (``validation_evidence_requirement``,
``dependencies``).

The frozen thirteen are pinned independently through exact equality
(``set(MIGRATED_IDENTITIES) == register o3_complete``); merged rows, removed
rows, runtime-strategy metadata, and other non-target records are outside the
target scan; prose is never scanned. Coverage fails closed if any O4 target
is missing from the review or the O1 reviewed-decision entries.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES
from scripts import check_o4_lifecycle_consistency as lifecycle

REPO = Path(__file__).resolve().parents[1]

#: The four non-O3 identities corrected by the O4 lifecycle-consistency
#: correction (their future O3-transition obligations were removed).
CORRECTED_NON_O3 = (
    "MethodEvaluationScope",
    "realizedBy",
    "specifiesFunction",
    "hasRelevantEvidenceContract",
)

#: Non-target register rows used to prove the target scoping (fixtures only —
#: never modified in the real tree).
MERGED_ROW = "IncrementTraceabilityShell"
REMOVED_ROW = "derivesNeedFromConcern"


def _fixture(tmp_path: Path) -> Path:
    """A minimal root holding the three invariant-scanned artifacts."""
    for rel in (
        lifecycle.O1_DECISIONS_PATH,
        lifecycle.REVIEW_PATH,
        lifecycle.REGISTER_PATH,
    ):
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, target)
    return tmp_path


def _register(root: Path) -> dict:
    return json.loads((root / lifecycle.REGISTER_PATH).read_text(encoding="utf-8"))


def _write_register(root: Path, document: dict) -> None:
    (root / lifecycle.REGISTER_PATH).write_text(
        json.dumps(document, indent=1) + "\n", encoding="utf-8"
    )


def test_repository_is_clean() -> None:
    assert lifecycle.run_all_checks(REPO) == []


def test_exact_o4_target_count_and_o3_equality() -> None:
    document = _register(REPO)
    o4_targets = {
        row["identity"]
        for row in document["rows"]
        if row.get("membership") == "o4-target"
    }
    o3_complete = {
        row["identity"] for row in document["rows"] if row.get("o3_complete") is True
    }
    assert len(o4_targets) == 77
    assert len(o3_complete) == 13
    assert set(MIGRATED_IDENTITIES) == o3_complete
    assert o4_targets.isdisjoint(o3_complete)
    assert set(CORRECTED_NON_O3).issubset(o4_targets)


def test_frozen_thirteen_retain_their_o3_evidence() -> None:
    # The frozen-thirteen exemption is real and load-bearing: those rows
    # legitimately keep O3 transition evidence and are never scanned.
    document = _register(REPO)
    rows = {row["identity"]: row for row in document["rows"]}
    retained = [
        identity
        for identity in MIGRATED_IDENTITIES
        if any(
            lifecycle.is_o3_lifecycle_obligation(item)
            for item in rows[identity]["validation_evidence_requirement"]
        )
    ]
    assert retained, "expected the frozen thirteen to retain O3 transition evidence"


def test_mutation_register_target_obligation_fails(tmp_path) -> None:
    root = _fixture(tmp_path)
    document = _register(root)
    for row in document["rows"]:
        if row["identity"] == "MethodEvaluationScope":
            row["validation_evidence_requirement"] = list(
                row["validation_evidence_requirement"]
            ) + ["O3 approved authority transition"]
    _write_register(root, document)
    errors = lifecycle.run_all_checks(root)
    assert any(
        "MethodEvaluationScope" in error
        and "validation_evidence_requirement" in error
        for error in errors
    )


def test_mutation_review_target_obligation_fails(tmp_path) -> None:
    root = _fixture(tmp_path)
    path = root / lifecycle.REVIEW_PATH
    document = json.loads(path.read_text(encoding="utf-8"))
    for row in document["rows"]:
        if row["identity"] == "realizedBy":
            row["target"]["evidence_needed"] = list(
                row["target"]["evidence_needed"]
            ) + ["future O3 transition"]
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    errors = lifecycle.run_all_checks(root)
    assert any(
        "realizedBy" in error and "evidence_needed" in error for error in errors
    )


def test_mutation_o1_target_obligation_fails(tmp_path) -> None:
    root = _fixture(tmp_path)
    path = root / lifecycle.O1_DECISIONS_PATH
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    entry = document["entries"]["specifiesFunction"]
    entry["required_evidence"] = list(entry["required_evidence"]) + ["O3 admission"]
    path.write_text(
        yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    errors = lifecycle.run_all_checks(root)
    assert any(
        "specifiesFunction" in error and "required_evidence" in error
        for error in errors
    )


def test_mutation_frozen_identity_obligation_is_exempt(tmp_path) -> None:
    root = _fixture(tmp_path)
    document = _register(root)
    for row in document["rows"]:
        if row["identity"] == "MethodPhase":
            row["validation_evidence_requirement"] = list(
                row["validation_evidence_requirement"]
            ) + ["O3 approved authority transition"]
    _write_register(root, document)
    assert lifecycle.run_all_checks(root) == []


def test_non_target_metadata_is_outside_the_target_scan(tmp_path) -> None:
    # Fixture-only: an O3 phrase planted on a merged row (register) and on a
    # removed row (O1 decisions) must NOT cause an O4-target lifecycle
    # failure — the checker implements the declared target scope.
    root = _fixture(tmp_path)
    document = _register(root)
    for row in document["rows"]:
        if row["identity"] == MERGED_ROW:
            assert row.get("membership") != "o4-target"
            row["validation_evidence_requirement"] = list(
                row.get("validation_evidence_requirement") or []
            ) + ["O3 approved authority transition"]
    _write_register(root, document)

    path = root / lifecycle.O1_DECISIONS_PATH
    decisions = yaml.safe_load(path.read_text(encoding="utf-8"))
    removed = decisions["entries"][REMOVED_ROW]
    removed["required_evidence"] = list(removed.get("required_evidence") or []) + [
        "O3 transition"
    ]
    path.write_text(
        yaml.safe_dump(decisions, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    assert lifecycle.run_all_checks(root) == []


def test_contextual_o3_prose_is_not_a_violation(tmp_path) -> None:
    root = _fixture(tmp_path)
    path = root / lifecycle.O1_DECISIONS_PATH
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    entry = document["entries"]["specifiesFunction"]
    entry["note"] = (
        (entry.get("note") or "")
        + " Historical note: the O3 transition completed for the frozen thirteen."
    )
    path.write_text(
        yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    assert lifecycle.run_all_checks(root) == []


def test_coverage_fails_when_a_target_is_missing_from_the_review(tmp_path) -> None:
    root = _fixture(tmp_path)
    path = root / lifecycle.REVIEW_PATH
    document = json.loads(path.read_text(encoding="utf-8"))
    document["rows"] = [
        row for row in document["rows"] if row["identity"] != "MethodEvaluationScope"
    ]
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    errors = lifecycle.run_all_checks(root)
    assert any(
        "MethodEvaluationScope" in error and "integrated review" in error
        for error in errors
    )


def test_coverage_fails_when_a_target_is_missing_from_o1_decisions(tmp_path) -> None:
    root = _fixture(tmp_path)
    path = root / lifecycle.O1_DECISIONS_PATH
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    del document["entries"]["realizedBy"]
    path.write_text(
        yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    errors = lifecycle.run_all_checks(root)
    assert any(
        "realizedBy" in error and "O1 reviewed-decision entries" in error
        for error in errors
    )


def test_membership_derivation_fails_closed_on_shortfall(tmp_path) -> None:
    # If the register loses an O4 target from its membership accounting, the
    # checker must fail closed rather than silently scanning less.
    root = _fixture(tmp_path)
    document = _register(root)
    for row in document["rows"]:
        if row.get("membership") == "o4-target":
            row["membership"] = "o4-target-dropped"  # fixture-only
            break
    _write_register(root, document)
    errors = lifecycle.run_all_checks(root)
    assert any("o4_targets must be exactly 77" in error for error in errors)


def test_check_repo_fails_when_lifecycle_gate_fails() -> None:
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
        check_repo.generate_semantic_projection_v1, "run_check_errors", return_value=[]
    ), mock.patch.object(
        check_repo.generate_semantic_projection_o22, "run_check_errors_o22", return_value=[]
    ), mock.patch.object(
        check_repo.generate_semantic_projection_o23, "run_check_errors_o23", return_value=[]
    ), mock.patch.object(
        check_repo.generate_semantic_authority_inventory, "run_check_errors", return_value=[]
    ), mock.patch.object(
        check_repo.validate_review, "run_check_errors", return_value=[]
    ), mock.patch.object(
        check_repo.generate_o4_execution_register, "run_check_errors", return_value=[]
    ), mock.patch.object(
        check_repo.check_o4_lifecycle_consistency,
        "run_all_checks",
        return_value=["sentinel lifecycle-consistency error"],
    ):
        assert check_repo.main() == 1


def test_check_repo_invokes_the_lifecycle_gate() -> None:
    from unittest import mock

    from scripts import check_repo

    calls: list[int] = []
    original = check_repo.check_o4_lifecycle_consistency.run_all_checks

    def spy(root):
        calls.append(1)
        return original(root)

    with mock.patch.object(
        check_repo.check_o4_lifecycle_consistency,
        "run_all_checks",
        side_effect=spy,
    ):
        result = check_repo.main()
    assert calls, "check_repo did not invoke the O4 lifecycle-consistency gate"
    assert result == 0
