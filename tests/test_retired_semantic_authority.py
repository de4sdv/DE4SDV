"""Retired authority and machinery stay retired.

Guards against restoring the deleted authored ontology or its closed consumer
ledger. The runtime that read the ontology and the generator libraries that
produced the historical records are deleted too. The records the runtime still
serves are frozen and verified at their own revisions by
``scripts/verify_generated_chain.py``; the other historical records are
archived at the ``release-2026-10-11`` tag. These tests keep that frozen-record
check wired into ``scripts/check_repo.py``, keep deleted modules and files
absent, and keep build-time governance modules out of the runtime import graph.
"""
import importlib.util
from pathlib import Path
import subprocess
from unittest import mock

import pytest

from scripts import check_repo
from scripts import verify_generated_chain as verifier

ROOT = Path(__file__).resolve().parents[1]
RETIRED_AUTHORITY = "de4sdv-basic-ontology.yaml"
RETIRED_LEDGER = {
    "de4sdv/semantic/o4_consumers.py",
    "docs/method-conformance/o4/consumer-ledger.yaml",
    "tests/test_o4_consumer_ledger.py",
}
#: Records that moved out of docs/ with the contract data and name the deleted
#: file as provenance: the six frozen records never change, and the review is
#: the record of what was reviewed. Neither is an authority.
HISTORICAL_RECORDS = frozenset({
    "de4sdv/semantic/contract-data/ontology-review.json",
    *(
        f"de4sdv/semantic/contract-data/frozen-records/{name}"
        for name in (
            "api-representation-profile-v1.json",
            "api-representation-profile-v1.1.json",
            "api-representation-profile-v1.2.json",
            "semantic-projection-v1.json",
            "semantic-projection-v1.1.json",
            "semantic-projection-v1.2.json",
        )
    ),
})


def _assert_retirement(root, tracked):
    assert tracked, "tracked-file discovery must not be empty"
    assert not RETIRED_LEDGER.intersection(tracked), "closed ledger must stay retired"
    assert not any(Path(p).name.casefold() == RETIRED_AUTHORITY.casefold() for p in tracked)
    # Historical documents and test references are evidence, not live authorities.
    live = [
        p for p in tracked
        if not p.startswith(("docs/", "tests/")) and p not in HISTORICAL_RECORDS
    ]
    assert live, "live-source discovery must not be empty"
    marker = RETIRED_AUTHORITY.encode("ascii").lower()
    for relative in live:
        assert marker not in (root / relative).read_bytes().lower(), relative


def test_deleted_authority_and_closed_ledger_stay_retired(tmp_path):
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    _assert_retirement(ROOT, [p for p in tracked if p])
    # The exemption stays exact: every exempted record is tracked.
    assert HISTORICAL_RECORDS <= set(tracked)

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
        definition_projection, kernel_vocabulary_projection,
        external_reference_contract, vocabulary_carrier,
    )
    from scripts import check_repo

    return (
        mock.patch.object(vocabulary_carrier, "run_check_errors", return_value=[]),
        mock.patch.object(external_reference_contract, "run_check_errors", return_value=[]),
        mock.patch.object(definition_projection, "run_check_errors", return_value=[]),
        mock.patch.object(kernel_vocabulary_projection, "run_check_errors", return_value=[]),
        mock.patch.object(check_repo, "find_duplicate_global_packages", return_value={}),
        mock.patch.object(check_repo.validate_aebs_executable_bench, "validate_bench", return_value=[]),
        mock.patch.object(check_repo.check_model_sync, "run_all_checks", return_value=[]),
        mock.patch.object(check_repo.generate_scenario_manifest, "run_check_errors", return_value=[]),
        mock.patch.object(check_repo.check_naming, "run_all_checks", return_value=[]),
        mock.patch.object(check_repo.verify_generated_chain, "frozen_record_errors", return_value=[]),
        mock.patch.object(check_repo.generate_native_grounding_projection, "run_check_errors", return_value=[]),
    )


# ---------------------------------------------------------------------------
# Frozen records: check_repo runs their check
# ---------------------------------------------------------------------------

DELETED_MODULES = (
    "de4sdv.semantic.runtime",
    "de4sdv.semantic.runtime_composition",
    "de4sdv.semantic.authority_ids",
    "de4sdv.semantic.projection_v1",
    "de4sdv.semantic.projection_o22",
    "de4sdv.semantic.projection_o23",
    "de4sdv.semantic.o3_equivalence",
)
DELETED_FILES = (
    "approach/framework/ontology/de4sdv-basic-ontology.yaml",
    "scripts/run_o3_equivalence.py",
    "scripts/relationship_successor.py",
)


def test_check_repo_runs_the_frozen_record_check_and_fails_when_it_fails():
    source = (ROOT / "scripts/check_repo.py").read_text(encoding="utf-8")
    assert "verify_generated_chain.frozen_record_errors" in source
    with mock.patch.object(check_repo, "find_duplicate_global_packages", return_value={}), \
            mock.patch.object(check_repo.validate_aebs_executable_bench, "validate_bench",
                              return_value=[]), \
            mock.patch.object(check_repo.check_model_sync, "run_all_checks", return_value=[]), \
            mock.patch.object(check_repo.generate_scenario_manifest, "run_check_errors",
                              return_value=[]), \
            mock.patch.object(check_repo.check_naming, "run_all_checks", return_value=[]), \
            mock.patch.object(check_repo.verify_generated_chain, "frozen_record_errors",
                              return_value=["sentinel frozen-record error"]):
        assert check_repo.main() == 1


def test_frozen_record_check_passes_for_real_without_the_authored_ontology():
    assert not (ROOT / DELETED_FILES[0]).exists()
    assert verifier.frozen_record_errors(ROOT) == []


# ---------------------------------------------------------------------------
# Deleted machinery stays deleted
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module", DELETED_MODULES)
def test_deleted_module_is_absent(module):
    assert importlib.util.find_spec(module) is None, module


@pytest.mark.parametrize("path", DELETED_FILES)
def test_deleted_file_is_absent(path):
    assert not (ROOT / path).exists(), path


# ---------------------------------------------------------------------------
# Runtime import boundary
# ---------------------------------------------------------------------------

#: Build-time governance modules: the runtime never imports them, except the
#: construction verifiers listed below.
BUILD_TIME_GOVERNANCE_MODULES = (
    "authority_inventory.py",
    "relationship_successor_contract.py",
    "scoped_assurance.py",
    "definition_projection.py",
    "kernel_vocabulary_projection.py",
    "native_grounding_projection.py",
    "vocabulary_carrier.py",
)

#: Construction-time verifiers: runtime modules that verify build-time
#: artifacts once at construction. Only the named imports are allowed.
CONSTRUCTION_VERIFIER_IMPORTS = {
    "model_contract.py": frozenset({"relationship_successor_contract"}),
}


def test_runtime_never_imports_build_time_governance_modules():
    offenders: list[str] = []
    for path in sorted((ROOT / "de4sdv").rglob("*.py")):
        if "__pycache__" in path.parts or path.name in BUILD_TIME_GOVERNANCE_MODULES:
            continue
        text = path.read_text(encoding="utf-8")
        for marker in ("authority-review-decisions", "semantic-authority-inventory"):
            if marker in text:
                offenders.append(f"{path.relative_to(ROOT)}: {marker}")
        allowed = CONSTRUCTION_VERIFIER_IMPORTS.get(path.name, frozenset())
        for governance in BUILD_TIME_GOVERNANCE_MODULES:
            stem = governance[: -len(".py")]
            if stem in allowed:
                continue
            if f"import {stem}" in text or f"from .{stem}" in text:
                offenders.append(f"{path.relative_to(ROOT)}: imports {stem}")
    assert offenders == []
    for allowed in CONSTRUCTION_VERIFIER_IMPORTS.values():
        assert "authority_inventory" not in allowed
