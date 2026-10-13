"""Retired generator and runtime machinery stays retired.

The authored ontology, the runtime that read it and the generator libraries
that produced the historical records are deleted. The records the runtime
still serves are frozen and verified at their own revisions by the frozen lane
(``scripts/verify_generated_chain.py``); the other historical records are
archived at the ``release-2026-10-11`` tag. These tests keep the frozen lane
wired into ``scripts/check_repo.py``, keep deleted modules and files absent,
and keep build-time governance modules out of the runtime import graph.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest import mock

import pytest

from scripts import check_repo
from scripts import verify_generated_chain as verifier

REPO_ROOT = Path(__file__).resolve().parents[1]

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


# ---------------------------------------------------------------------------
# Frozen lane
# ---------------------------------------------------------------------------


def test_check_repo_runs_the_frozen_lane_and_fails_when_it_fails():
    source = (REPO_ROOT / "scripts/check_repo.py").read_text(encoding="utf-8")
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


def test_frozen_lane_passes_for_real_without_the_authored_ontology():
    assert not (REPO_ROOT / DELETED_FILES[0]).exists()
    assert verifier.frozen_record_errors(REPO_ROOT) == []


# ---------------------------------------------------------------------------
# Deleted machinery stays deleted
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module", DELETED_MODULES)
def test_deleted_module_is_absent(module):
    assert importlib.util.find_spec(module) is None, module


@pytest.mark.parametrize("path", DELETED_FILES)
def test_deleted_file_is_absent(path):
    assert not (REPO_ROOT / path).exists(), path


# ---------------------------------------------------------------------------
# Runtime import boundary (ported from test_semantic_authority_inventory.py)
# ---------------------------------------------------------------------------

#: Build-time governance modules: the runtime never imports them, except the
#: construction verifiers listed below.
BUILD_TIME_GOVERNANCE_MODULES = (
    "authority_inventory.py",
    "relationship_successor_contract.py",
    "scoped_assurance.py",
    "definition_projection.py",
    "definition_projection_batch2.py",
    "projection_o2p.py",
    "vocabulary_carrier.py",
)

#: Construction-time verifiers: runtime modules that verify build-time
#: artifacts once at construction. Only the named imports are allowed.
CONSTRUCTION_VERIFIER_IMPORTS = {
    "model_contract.py": frozenset({"relationship_successor_contract"}),
}


def test_runtime_never_imports_build_time_governance_modules():
    offenders: list[str] = []
    for path in sorted((REPO_ROOT / "de4sdv").rglob("*.py")):
        if "__pycache__" in path.parts or path.name in BUILD_TIME_GOVERNANCE_MODULES:
            continue
        text = path.read_text(encoding="utf-8")
        for marker in ("authority-review-decisions", "semantic-authority-inventory"):
            if marker in text:
                offenders.append(f"{path.relative_to(REPO_ROOT)}: {marker}")
        allowed = CONSTRUCTION_VERIFIER_IMPORTS.get(path.name, frozenset())
        for governance in BUILD_TIME_GOVERNANCE_MODULES:
            stem = governance[: -len(".py")]
            if stem in allowed:
                continue
            if f"import {stem}" in text or f"from .{stem}" in text:
                offenders.append(f"{path.relative_to(REPO_ROOT)}: imports {stem}")
    assert offenders == []
    for allowed in CONSTRUCTION_VERIFIER_IMPORTS.values():
        assert "authority_inventory" not in allowed
