"""O4 execution register: machine accounting for the governed review targets.

The register MUST account for every reviewed identity exactly once
(93 = 90 retained + 1 removal + 2 merges), mark the frozen O3 13 complete
outside all O4 waves, give every retained O4 target exactly one base
(semantic treatment) wave, and hold gated rows at the W7 decision gate with
their curated, machine-checked base-wave re-entry destination. The register
is deterministically generated from the governed integrated review using
reviewed, machine-checked wave-mapping rules — the same generator/check runs
in scripts/check_repo.py, so a review edit that invalidates a mapping
assumption fails the gate.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from scripts import generate_o4_execution_register as gen

REPO = Path(__file__).resolve().parents[1]
REGISTER = REPO / "docs/method-conformance/o4/o4-execution-register.json"
REVIEW = REPO / "docs/method-conformance/o4/ontology-review/integrated-review.json"
REVIEW_MD = REPO / "docs/method-conformance/o4/ontology-review/REVIEW.md"

EXPECTED_BASE_WAVE_COUNTS = {
    "W2": 35,
    "W3": 11,
    "W4": 10,
    "W5": 11,
    "W6": 9,
    "closure": 1,
}
EXPECTED_GATED_TOTAL = 11


def _register() -> dict:
    return json.loads(REGISTER.read_text(encoding="utf-8"))


def _rows_by_identity(register: dict) -> dict:
    return {row["identity"]: row for row in register["rows"]}


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
    removed = [row for row in rows if row["accounting_status"] == "removed"]
    assert [row["identity"] for row in removed] == ["derivesNeedFromConcern"]


def test_merge_targets_resolve_non_vacuously() -> None:
    by = _rows_by_identity(_register())

    validates = by["validatesFitnessForUse"]
    assert validates["accounting_status"] == "merged"
    assert validates["merge_into"] == "validatedBy"
    assert by["validatedBy"]["accounting_status"] == "retained"

    shell = by["IncrementTraceabilityShell"]
    assert shell["accounting_status"] == "merged"
    assert shell["merge_into"] == "RequiredTraceChain"
    assert by["RequiredTraceChain"]["accounting_status"] == "retained"
    note = shell["merge_note"]
    assert "decision-15" in note
    assert "pending" in note and "not yet decided" in note, (
        "the shell merge must not pretend the final successor identity is decided"
    )


def test_frozen_o3_thirteen_binds_to_runtime_code() -> None:
    from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES

    register = _register()
    o3_rows = sorted(row["identity"] for row in register["rows"] if row["o3_complete"])
    assert o3_rows == sorted(MIGRATED_IDENTITIES)
    for row in register["rows"]:
        if row["o3_complete"]:
            assert row["base_wave"] == "O3-complete"
            assert row["gate_wave"] is None


def test_every_o4_target_has_exactly_one_base_wave() -> None:
    register = _register()
    targets = [
        row
        for row in register["rows"]
        if row["accounting_status"] == "retained" and not row["o3_complete"]
    ]
    assert len(targets) == 77
    counts: dict[str, int] = {}
    for row in targets:
        wave = row["base_wave"]
        assert wave in EXPECTED_BASE_WAVE_COUNTS, f"{row['identity']} has base wave {wave!r}"
        assert row["wave_basis"], f"{row['identity']} lacks a wave basis"
        counts[wave] = counts.get(wave, 0) + 1
    assert counts == EXPECTED_BASE_WAVE_COUNTS
    assert register["accounting"]["by_base_wave"] == EXPECTED_BASE_WAVE_COUNTS
    assert register["accounting"]["gated_total"] == EXPECTED_GATED_TOTAL


def test_gated_rows_carry_base_and_gate_representation() -> None:
    register = _register()
    gated = [row for row in register["rows"] if row["gate_wave"] == "W7"]
    assert len(gated) == EXPECTED_GATED_TOTAL
    for row in gated:
        assert row["base_wave"] in {"W2", "W3", "W5"}, row["identity"]
        assert row["gate_decisions"] or row["blockers"], row["identity"]
        assert row["wave_basis"].startswith("W7 gate re-entry"), row["identity"]
    by = _rows_by_identity(register)
    assert by["allocatedTo"]["base_wave"] == "W3"
    assert by["instantiatesCanonicalArchitecture"]["base_wave"] == "W5"
    assert by["instantiatesCanonicalArchitecture"]["gate_decisions"] == ["decision-10"]
    for name in ("ArchitectureElement", "Function", "LogicalElement", "PhysicalElement"):
        assert by[name]["base_wave"] == "W2"
        assert by[name]["gate_decisions"] == ["decision-5"]
    for row in register["rows"]:
        if row["accounting_status"] == "retained" and row["gate_wave"] is None:
            assert not row["identity"] in gen.W7_BASE_MAP


def test_curated_mapping_rules_still_agree_with_the_review() -> None:
    by = _rows_by_identity(_register())
    for identity, expected in gen.W3_EXPECTED_CLASSES.items():
        assert by[identity]["base_wave"] == "W3"
        assert by[identity]["migration_class"] == expected
    for identity, expected in gen.W4_EXPECTED_CLASSES.items():
        assert by[identity]["base_wave"] == "W4"
        assert by[identity]["migration_class"] == expected
        assert by[identity]["blockers"] == []
    for identity, expected in gen.W6_EXPECTED_CLASSES.items():
        assert by[identity]["base_wave"] == "W6"
        assert by[identity]["migration_class"] == expected
    # W7-gated rows still carry the decision/blocker that caused them to be gated.
    assert by["EvidenceContract"]["blockers"]
    assert by["hasRelevantEvidenceContract"]["blockers"]
    assert by["allocatedTo"]["blockers"]
    assert by["AssuranceClaim"]["gate_decisions"] == ["decision-3"]
    assert by["AcceptanceCriterion"]["gate_decisions"] == ["decision-6"]
    assert by["hasAcceptanceCriterion"]["gate_decisions"] == ["decision-6"]
    # hasEvidenceStatus: structured classification wins over the burn-down prose.
    assert by["hasEvidenceStatus"]["base_wave"] == "W6"
    assert by["hasEvidenceStatus"]["migration_class"] == "REQUIRES_SEMANTIC_MIGRATION"


def test_blocker_groups_and_decisions_are_preserved() -> None:
    register = _register()
    decisions = register["review_open_decisions"]
    assert [item["id"] for item in decisions] == [f"decision-{n}" for n in range(1, 16)]
    assert decisions[0]["decision"].startswith("Approve the five renames")
    grouped = set()
    held = 0
    for wave, entry in register["blockers_by_wave"].items():
        assert wave in EXPECTED_BASE_WAVE_COUNTS or wave in {"W0", "W1"}
        grouped.update(entry["review_open_decisions"])
        held += len(entry["held_in_gate"])
    assert held == EXPECTED_GATED_TOTAL
    assert {"decision-1", "decision-5", "decision-6", "decision-9", "decision-10"}.issubset(grouped)
    # Decision-9 covers configurator/selection rows only.
    d9 = [item for item in decisions if item["id"] == "decision-9"][0]
    assert d9["rows"] == [
        "FeatureConfiguration",
        "selectsFeature",
        "appliesToMemberProduct",
        "includesCommonCapability",
        "selectsVariant",
    ]


def test_interpretations_record_the_documented_deviations() -> None:
    register = _register()
    interpretations = register["interpretations"]
    assert len(interpretations) >= 5
    by_id = {item["id"]: item for item in interpretations}
    assert "hasEvidenceStatus" in by_id["interp-3"]["rows"]
    assert "VariationPoint" in by_id["interp-5"]["rows"]
    assert by_id["interp-4"]["rows"] == sorted(gen.W7_BASE_MAP)


def _mutated_repo(tmp_path: Path, mutate) -> Path:
    """Copy the governed review + register into tmp_path and apply a mutation."""
    for rel in (
        gen.REVIEW_PATH,
        gen.REVIEW_MD_PATH,
        gen.REGISTER_PATH,
    ):
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, target)
    review = json.loads((tmp_path / gen.REVIEW_PATH).read_text(encoding="utf-8"))
    mutate(review)
    (tmp_path / gen.REVIEW_PATH).write_text(json.dumps(review, indent=2), encoding="utf-8")
    return tmp_path


def test_review_edit_that_breaks_a_merge_binding_fails_the_gate(tmp_path: Path) -> None:
    def mutate(review: dict) -> None:
        for row in review["rows"]:
            if row["identity"] == "validatesFitnessForUse":
                row["target"]["merge_into"] = "somewhereElse"

    errors = gen.run_check_errors(_mutated_repo(tmp_path, mutate))
    assert errors, "a broken merge binding must fail the register gate"


def test_review_edit_that_invalidates_a_curated_wave_mapping_fails_the_gate(tmp_path: Path) -> None:
    def mutate(review: dict) -> None:
        for row in review["rows"]:
            if row["identity"] == "Concern":
                row["migration_class"] = "MODEL_AUTHORITY_PARITY"

    errors = gen.run_check_errors(_mutated_repo(tmp_path, mutate))
    assert errors, "an invalidated curated wave mapping must fail the register gate"
