"""O4 execution register: machine accounting for the governed review targets.

The register MUST account for every reviewed identity exactly once (93 = 90
retained + 1 removal + 2 merges), mark the frozen O3 13 complete outside all
O4 waves, and assign every retained O4 target exactly one proposed migration
wave by the documented rules. The register is a reproducible derivation of
the accepted review — the same generator/check runs in scripts/check_repo.py.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts import generate_o4_execution_register as gen

REPO = Path(__file__).resolve().parents[1]
REGISTER = REPO / "docs/method-conformance/o4/o4-execution-register.json"
EXPECTED_WAVE_COUNTS = {
    "W2": 26,
    "W3": 10,
    "W4": 10,
    "W5": 10,
    "W6": 9,
    "W7": 11,
    "closure": 1,
}


def _register() -> dict:
    return json.loads(REGISTER.read_text(encoding="utf-8"))


def test_register_is_a_reproducible_derivation_of_the_governed_review() -> None:
    assert gen.run_check_errors(REPO) == []


def test_register_accounts_for_every_reviewed_identity_exactly_once() -> None:
    register = _register()
    rows = register["rows"]
    identities = [row["identity"] for row in rows]
    assert len(identities) == 93
    assert len(set(identities)) == 93, "duplicate identity in register"

    accounting = register["accounting"]
    assert accounting["total_reviewed"] == 93
    assert accounting["retained_total"] == 90
    assert accounting["merged"] == 2
    assert accounting["removed"] == 1
    assert accounting["o4_targets"] == 77
    assert accounting["o3_complete"] == 13

    merged = [row for row in rows if row["accounting_status"] == "merged"]
    assert sorted(row["identity"] for row in merged) == [
        "IncrementTraceabilityShell",
        "validatesFitnessForUse",
    ]
    for row in merged:
        assert row["merge_into"], f"{row['identity']} lacks merge target"
    removed = [row for row in rows if row["accounting_status"] == "removed"]
    assert [row["identity"] for row in removed] == ["derivesNeedFromConcern"]

    # Every merge target must name an accounted retained identity.
    for row in merged:
        target_name = row["merge_into"]
        assert any(
            other["identity"] in target_name or other["merge_into"] is None
            for other in rows
        ), f"merge target for {row['identity']} not resolvable among retained rows"


def test_frozen_o3_thirteen_binds_to_runtime_code() -> None:
    from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES

    register = _register()
    o3_rows = sorted(row["identity"] for row in register["rows"] if row["o3_complete"])
    assert o3_rows == sorted(MIGRATED_IDENTITIES)
    for row in register["rows"]:
        if row["o3_complete"]:
            assert row["proposed_wave"] == "O4-complete"


def test_every_o4_target_has_exactly_one_documented_wave() -> None:
    register = _register()
    targets = [
        row
        for row in register["rows"]
        if row["accounting_status"] == "retained" and not row["o3_complete"]
    ]
    assert len(targets) == 77
    counts: dict[str, int] = {}
    for row in targets:
        wave = row["proposed_wave"]
        assert wave in EXPECTED_WAVE_COUNTS, f"{row['identity']} has wave {wave!r}"
        assert row["wave_basis"], f"{row['identity']} lacks a wave basis"
        counts[wave] = counts.get(wave, 0) + 1
    assert counts == EXPECTED_WAVE_COUNTS
    assert register["accounting"]["by_wave"] == EXPECTED_WAVE_COUNTS


def test_blocker_groups_and_decisions_are_preserved() -> None:
    register = _register()
    decision_ids = {item["id"] for item in register["review_open_decisions"]}
    assert len(decision_ids) == 15 and all(
        item_id.startswith("decision-") for item_id in decision_ids
    )
    grouped = set()
    for wave, entry in register["blockers_by_wave"].items():
        assert wave in EXPECTED_WAVE_COUNTS or wave in {"W0", "W1"}
        grouped.update(entry["review_open_decisions"])
    # The five owner-decision items named in the review's closure discussion
    # are exactly the decisions that gate waves.
    assert {
        "decision-1", "decision-5", "decision-6", "decision-9", "decision-10",
    }.issubset(grouped)
