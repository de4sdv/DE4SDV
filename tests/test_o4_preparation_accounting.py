"""Fail-closed preparation accounting, not authority activation."""
from pathlib import Path

import pytest


def test_duplicate_identity_is_not_hidden_by_indexing():
    from de4sdv.semantic.o4_preparation import unique_index, PreparationError

    with pytest.raises(PreparationError, match="duplicate"):
        unique_index([{"identity": "Synthetic"}, {"identity": "Synthetic"}], "fixture")


def test_accounting_is_complete_and_never_claims_retirement():
    from de4sdv.semantic.o4_preparation import build_accounting

    register = [{"identity": "Frozen", "membership": "o3-complete", "o3_complete": True,
                 "base_wave": "O3-complete", "gate_wave": None},
                {"identity": "Candidate", "membership": "o4-target", "o3_complete": False,
                 "base_wave": "W4", "gate_wave": None}]
    inventory = [{"identity": name, "reviewed": {"stage": "pending", "authority_current": "legacy-yaml",
                  "required_evidence": ["review"]}} for name in ("Frozen", "Candidate")]
    result = build_accounting(register, inventory, {"Frozen"}, {"Candidate"}, set(), set())
    assert result["closure_proven"] is False
    assert result["waves"]["W4"]["projection_outputs"] == ["Candidate"]
    assert result["waves"]["W4"]["targets"] == ["Candidate"]
    assert result["rows"][1]["retirement_proven"] is False


def test_missing_inventory_and_unknown_output_fail_closed():
    from de4sdv.semantic.o4_preparation import build_accounting, PreparationError

    rows = [{"identity": "Only", "membership": "o3-complete", "o3_complete": True,
             "base_wave": "O3-complete", "gate_wave": None}]
    with pytest.raises(PreparationError, match="inventory"):
        build_accounting(rows, [], {"Only"}, set(), set(), set())
    inv = [{"identity": "Only", "reviewed": {}}]
    with pytest.raises(PreparationError, match="unknown output"):
        build_accounting(rows, inv, {"Only"}, {"Foreign"}, set(), set())
    with pytest.raises(PreparationError, match="frozen"):
        build_accounting(rows, inv, {"Extra"}, set(), set(), set())
