"""O4 Wave C2: retired O1/O2/O3 generator and runtime machinery.

Wave C2 deleted the authored ontology, the O3 bundle runtime, the legacy
runtime and the O1/O2 v1-v1.2/O3-scope generator libraries (they read the
authored ontology). Their outputs are frozen records verified historically by
the frozen lane (``scripts/verify_generated_chain.py``). These tests replace
the frozen-record and import-boundary tests that lived in the deleted
generator test files:

- ``test_semantic_authority_inventory.py`` (``test_committed_artifacts_are_frozen_records``,
  ``test_check_repo_runs_the_frozen_lane``,
  ``test_check_repo_passes_when_the_frozen_lane_passes``,
  ``TestRuntimeBoundary::test_reviewed_decisions_not_runtime_values``);
- ``test_semantic_projection_v1.py`` / ``_o22.py`` / ``_o23.py``
  (``test_committed_artifacts_are_frozen_records``,
  ``test_check_repo_fails_when_the_frozen_lane_fails``,
  ``test_check_repo_passes_when_all_gates_pass``,
  ``test_check_repo_actually_invokes_the_frozen_lane``,
  ``test_check_repo_registers_the_frozen_lane_not_v12_regeneration``,
  ``test_v1_pair_still_valid_as_a_frozen_record``,
  ``test_v11_pair_still_valid_as_a_frozen_record``);
- ``test_o3_equivalence_readiness.py``
  (``test_running_the_generator_changes_no_protected_file``).
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from scripts import check_repo
from scripts import verify_generated_chain as verifier

REPO_ROOT = Path(__file__).resolve().parents[1]

RETIRED_CLIS = sorted(set(verifier.RETIRED_GENERATORS.values()))
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
# Frozen records and retired generators
# ---------------------------------------------------------------------------


def test_retired_generator_outputs_are_frozen_records():
    manifest = json.loads((REPO_ROOT / verifier.FROZEN_MANIFEST_PATH).read_text(encoding="utf-8"))
    pinned = {record["path"]: record for record in manifest["records"]}
    entries = {entry["artifact"]: entry for entry in verifier._frozen_lane_entries(REPO_ROOT)}
    for path, generator in verifier.RETIRED_GENERATORS.items():
        assert pinned[path]["retired_generator"] == generator, path
        assert entries[path]["ok"], entries[path]


@pytest.mark.parametrize("cli", RETIRED_CLIS)
@pytest.mark.parametrize("args", [[], ["--check"]])
def test_retired_generator_cli_refuses_without_its_library(cli, args):
    before = subprocess.run(["git", "status", "--porcelain", "--", "docs/method-conformance"],
                            cwd=REPO_ROOT, capture_output=True, text=True).stdout
    result = subprocess.run([sys.executable, str(REPO_ROOT / cli), *args], cwd=REPO_ROOT,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 2, result.stderr
    assert "is retired" in result.stdout and "frozen-records.json" in result.stdout
    assert "Traceback" not in result.stderr
    after = subprocess.run(["git", "status", "--porcelain", "--", "docs/method-conformance"],
                           cwd=REPO_ROOT, capture_output=True, text=True).stdout
    assert after == before


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


def test_o3_bundle_name_is_only_the_frozen_identity_list():
    """projection_o2p.py (a bound input of the live O2+ pair) imports the frozen
    O3-migrated identity list from this module name; nothing else survives."""
    from de4sdv.semantic import model_contract, o3_bundle

    assert o3_bundle.MIGRATED_IDENTITIES == model_contract.O2_CHAIN_IDENTITIES
    assert o3_bundle.MIGRATED_CLASSES == model_contract.O2_CHAIN_CLASSES
    assert o3_bundle.MIGRATED_RELATIONSHIPS == model_contract.O2_CHAIN_RELATIONSHIPS
    public = {name for name in vars(o3_bundle) if not name.startswith("_")}
    assert public - {"annotations"} == {"MIGRATED_IDENTITIES", "MIGRATED_CLASSES",
                                        "MIGRATED_RELATIONSHIPS"}


# ---------------------------------------------------------------------------
# Runtime import boundary (ported from test_semantic_authority_inventory.py)
# ---------------------------------------------------------------------------

#: Build-time governance modules: the runtime never imports them, except the
#: construction verifiers listed below.
BUILD_TIME_GOVERNANCE_MODULES = (
    "authority_inventory.py",
    "definition_candidate.py",
    "definition_candidate_provider.py",
    "definition_migration.py",
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
    "model_authority_runtime.py": frozenset({"definition_migration"}),
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
