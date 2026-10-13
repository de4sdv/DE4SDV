"""Guard against restoring the deleted authority or its closed consumer ledger."""
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
RETIRED_AUTHORITY = "de4sdv-basic-ontology.yaml"
RETIRED_LEDGER = {
    "de4sdv/semantic/o4_consumers.py",
    "docs/method-conformance/o4/consumer-ledger.yaml",
    "tests/test_o4_consumer_ledger.py",
}
HISTORICAL_TOOL = "scripts/ontology_review/arch_recheck.py"


def _assert_retirement(root, tracked):
    assert tracked, "tracked-file discovery must not be empty"
    assert not RETIRED_LEDGER.intersection(tracked), "closed ledger must stay retired"
    assert not any(Path(p).name.casefold() == RETIRED_AUTHORITY.casefold() for p in tracked)
    # Historical documents and test references are evidence, not live authorities.
    live = [p for p in tracked if not p.startswith(("docs/", "tests/"))
            and p != HISTORICAL_TOOL]
    assert live, "live-source discovery must not be empty"
    marker = RETIRED_AUTHORITY.encode("ascii").lower()
    for relative in live:
        assert marker not in (root / relative).read_bytes().lower(), relative


def test_deleted_authority_and_closed_ledger_stay_retired(tmp_path):
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    _assert_retirement(ROOT, [p for p in tracked if p])

    source = tmp_path / "de4sdv" / "example.asset"
    source.parent.mkdir()
    source.write_bytes(b"model-owned semantic data")
    _assert_retirement(tmp_path, ["de4sdv/example.asset"])
    source.write_bytes(RETIRED_AUTHORITY.upper().encode("ascii"))
    with pytest.raises(AssertionError, match="example.asset"):
        _assert_retirement(tmp_path, ["de4sdv/example.asset"])
    with pytest.raises(AssertionError):
        _assert_retirement(tmp_path, ["elsewhere/" + RETIRED_AUTHORITY.upper()])
    with pytest.raises(AssertionError, match="must not be empty"):
        _assert_retirement(tmp_path, [])
    with pytest.raises(AssertionError, match="closed ledger"):
        _assert_retirement(tmp_path, [*sorted(RETIRED_LEDGER), "de4sdv/example.asset"])


def _passing_gate_mocks():
    """Shared passing controls for independent aggregate-gate attribution tests."""
    from unittest import mock
    from de4sdv.semantic import (
        definition_projection, definition_projection_batch2,
        external_reference_contract, vocabulary_carrier,
    )
    from scripts import check_repo

    return (
        mock.patch.object(vocabulary_carrier, "run_check_errors", return_value=[]),
        mock.patch.object(external_reference_contract, "run_check_errors", return_value=[]),
        mock.patch.object(definition_projection, "run_check_errors", return_value=[]),
        mock.patch.object(definition_projection_batch2, "run_check_errors", return_value=[]),
        mock.patch.object(check_repo, "find_duplicate_global_packages", return_value={}),
        mock.patch.object(check_repo.validate_aebs_executable_bench, "validate_bench", return_value=[]),
        mock.patch.object(check_repo.check_model_sync, "run_all_checks", return_value=[]),
        mock.patch.object(check_repo.generate_scenario_manifest, "run_check_errors", return_value=[]),
        mock.patch.object(check_repo.check_naming, "run_all_checks", return_value=[]),
        mock.patch.object(check_repo.verify_generated_chain, "frozen_record_errors", return_value=[]),
        mock.patch.object(check_repo.generate_semantic_projection_o2p, "run_check_errors_o2p", return_value=[]),
        mock.patch.object(check_repo.validate_review, "run_check_errors", return_value=[]),
        mock.patch.object(check_repo.generate_o4_execution_register, "run_check_errors", return_value=[]),
        mock.patch.object(check_repo.check_o4_lifecycle_consistency, "run_all_checks", return_value=[]),
    )
