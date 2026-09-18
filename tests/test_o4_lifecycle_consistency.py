"""O4 lifecycle-consistency invariant tests: O3 stays frozen throughout O4.

The invariant (``scripts/check_o4_lifecycle_consistency.py``, wired into
``check_repo.py``) forbids future O3 authority-transition/admission
obligations for every O4-target identity outside the frozen thirteen
``MIGRATED_IDENTITIES`` — in the O1 reviewed decisions
(``required_evidence``), the accepted O4 review (``target.evidence_needed``,
``dependencies``), and the generated O4 execution register
(``validation_evidence_requirement``, ``dependencies``). It scans only those
structured lifecycle fields, never prose, so historical/contextual O3
mentions — and the thirteen identities' legitimately retained O3 transition
evidence — are not violations.

The mutation tests prove that adding an O3-transition obligation back to a
non-O3 row fails the repository gate, while the same wording on a frozen
identity or in prose stays exempt.
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


def test_repository_is_clean() -> None:
    assert lifecycle.run_all_checks(REPO) == []


def test_frozen_thirteen_and_disjoint_corrected_rows() -> None:
    assert len(MIGRATED_IDENTITIES) == 13
    assert set(CORRECTED_NON_O3).isdisjoint(set(MIGRATED_IDENTITIES))


def test_frozen_thirteen_retain_their_o3_evidence() -> None:
    # The exemption is real and load-bearing: the thirteen legitimately keep
    # O3 transition evidence, and the invariant never flags them.
    register = json.loads(
        (REPO / lifecycle.REGISTER_PATH).read_text(encoding="utf-8")
    )
    rows = {row["identity"]: row for row in register["rows"]}
    retained = [
        identity
        for identity in MIGRATED_IDENTITIES
        if any(
            lifecycle.is_o3_lifecycle_obligation(item)
            for item in rows[identity]["validation_evidence_requirement"]
        )
    ]
    assert retained, "expected the frozen thirteen to retain O3 transition evidence"


def test_mutation_register_obligation_fails(tmp_path) -> None:
    root = _fixture(tmp_path)
    path = root / lifecycle.REGISTER_PATH
    document = json.loads(path.read_text(encoding="utf-8"))
    for row in document["rows"]:
        if row["identity"] == "MethodEvaluationScope":
            row["validation_evidence_requirement"] = list(
                row["validation_evidence_requirement"]
            ) + ["O3 approved authority transition"]
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    errors = lifecycle.run_all_checks(root)
    assert any(
        "MethodEvaluationScope" in error
        and "validation_evidence_requirement" in error
        for error in errors
    )


def test_mutation_review_evidence_fails(tmp_path) -> None:
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


def test_mutation_o1_yaml_obligation_fails(tmp_path) -> None:
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
    path = root / lifecycle.REGISTER_PATH
    document = json.loads(path.read_text(encoding="utf-8"))
    for row in document["rows"]:
        if row["identity"] == "MethodPhase":
            row["validation_evidence_requirement"] = list(
                row["validation_evidence_requirement"]
            ) + ["O3 approved authority transition"]
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
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
