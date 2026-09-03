"""Tests for the AEBS scenario manifest generator.

The manifest makes the SysML model the canonical source for scenario
vocabulary. These tests assert that the generator faithfully reflects the
enum members and definitions declared in the verification .sysml files.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT / "textual-notation-of-model/packages/features/aebs/scenario-manifest.json"
)
SCRIPT = ROOT / "scripts/generate_scenario_manifest.py"

# Import the generator module for direct unit-style assertions.
sys.path.insert(0, str(ROOT))
from scripts import generate_scenario_manifest as gen  # noqa: E402

ALL_INCREMENTS = ["009B", "009C", "009D", "009E", "009F", "009G", "009H", "009I"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def manifest() -> dict:
    return gen.generate_manifest()


@pytest.fixture(scope="module")
def tracked_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Schema and coverage
# ---------------------------------------------------------------------------

def test_manifest_schema_is_v1(manifest: dict) -> None:
    assert manifest["schema"] == "de4sdv.scenario-manifest.v1"


def test_generated_from_points_at_aebs_dir(manifest: dict) -> None:
    assert manifest["generated_from"] == "textual-notation-of-model/packages/features/aebs/"


def test_manifest_has_entries_for_all_eight_increments(manifest: dict) -> None:
    assert set(manifest["increments"]) == set(ALL_INCREMENTS)


def test_each_increment_declares_core_fields(manifest: dict) -> None:
    core = {
        "sysml_file",
        "package_name",
        "verification_def",
        "verification_usages",
        "scenario_identity_enum",
        "evidence_outcome_enum",
        "bench_definition",
    }
    for inc, entry in manifest["increments"].items():
        missing = core - set(entry)
        assert not missing, (inc, missing)
        assert (ROOT / "textual-notation-of-model/packages/features/aebs" / entry["sysml_file"]).exists(), inc


# ---------------------------------------------------------------------------
# Scenario identity enums (the canonical scenario vocabulary)
# ---------------------------------------------------------------------------

SCENARIO_IDENTITY_COUNTS = {
    "009D": 6,
    "009E": 4,
    "009F": 5,
    "009I": 2,
}

# De-numbered semantic enum names per increment (model-organization-audit.md M3).
SCENARIO_IDENTITY_ENUMS_EXPECTED = {
    "009D": "OverrideScenarioIdentity",
    "009E": "NonActivationScenarioIdentity",
    "009F": "DegradedInputScenarioIdentity",
    "009I": "RegulatoryCriterionScenarioIdentity",
}
EVIDENCE_OUTCOME_ENUMS_EXPECTED = {
    "009C": "PartialInterventionEvidenceOutcome",
    "009D": "OverrideEvidenceOutcome",
    "009E": "NonActivationEvidenceOutcome",
    "009F": "DegradedInputEvidenceOutcome",
    "009G": "PedestrianEvidenceOutcome",
    "009H": "BicycleEvidenceOutcome",
    "009I": "RegulatoryCriterionEvidenceOutcome",
}


@pytest.mark.parametrize("increment,expected_count", list(SCENARIO_IDENTITY_COUNTS.items()))
def test_scenario_identity_counts_match_sysml(manifest: dict, increment: str, expected_count: int) -> None:
    entry = manifest["increments"][increment]
    assert entry["scenario_identity_enum"] == SCENARIO_IDENTITY_ENUMS_EXPECTED[increment]
    identities = entry["scenario_identities"]
    assert len(identities) == expected_count, (increment, identities)


def test_009d_scenario_identities_match_sysml_enum(manifest: dict) -> None:
    assert manifest["increments"]["009D"]["scenario_identities"] == [
        "freshFalseControl",
        "freshTrueOverride",
        "staleOverride",
        "missingOverride",
        "malformedOverride",
        "futureStampedOverride",
    ]


def test_009i_scenario_identities_are_pedestrian_and_bicycle(manifest: dict) -> None:
    assert manifest["increments"]["009I"]["scenario_identities"] == [
        "pedestrianCriterion",
        "bicycleCriterion",
    ]


def test_009e_scenario_identities(manifest: dict) -> None:
    assert manifest["increments"]["009E"]["scenario_identities"] == [
        "clearPath",
        "adjacentObject",
        "nonClosingTarget",
        "belowTrigger",
    ]


def test_009f_scenario_identities(manifest: dict) -> None:
    assert manifest["increments"]["009F"]["scenario_identities"] == [
        "staleInput",
        "missingInput",
        "malformedInput",
        "inconsistentInput",
        "unavailableInput",
    ]


# ---------------------------------------------------------------------------
# Increments without ScenarioIdentity
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("increment", ["009B", "009C", "009G", "009H"])
def test_increments_without_scenario_identity(manifest: dict, increment: str) -> None:
    entry = manifest["increments"][increment]
    assert entry["scenario_identity_enum"] is None
    assert "scenario_identities" not in entry


@pytest.mark.parametrize("increment,target", [("009G", "pedestrian"), ("009H", "bicycle")])
def test_target_type_increments_mark_target_as_identity(manifest: dict, increment: str, target: str) -> None:
    entry = manifest["increments"][increment]
    assert entry["target_type"] == target
    assert entry["target_type_is_distinguishing_identity"] is True


# ---------------------------------------------------------------------------
# Evidence outcome enums
# ---------------------------------------------------------------------------

def test_every_increment_with_enum_has_outcomes(manifest: dict) -> None:
    for inc, entry in manifest["increments"].items():
        if entry["evidence_outcome_enum"] is not None:
            assert entry["evidence_outcome_enum"] == EVIDENCE_OUTCOME_ENUMS_EXPECTED.get(inc)
            assert entry["evidence_outcomes"], inc


def test_009d_evidence_outcomes(manifest: dict) -> None:
    assert manifest["increments"]["009D"]["evidence_outcomes"] == [
        "passBoundedScenario",
        "failObservedBehavior",
        "inconclusiveCoverage",
        "errorEvidence",
    ]


# ---------------------------------------------------------------------------
# Verification defs and usages
# ---------------------------------------------------------------------------

def test_009b_has_single_nominal_verification(manifest: dict) -> None:
    entry = manifest["increments"]["009B"]
    assert entry["verification_def"] == "NominalMovingVehicleTargetVerification"
    assert entry["verification_usages"] == ["nominalMovingVehicleTargetVerification"]
    assert entry["bench_definition"] == "NominalMovingVehicleTargetBench"


def test_009c_has_single_partial_intervention_usage(manifest: dict) -> None:
    entry = manifest["increments"]["009C"]
    assert entry["verification_def"] == "NativeInterventionToMRMVerification"
    assert entry["verification_usages"] == ["nativeInterventionToMRMVerification"]
    assert entry["bench_definition"] == "NativeInterventionBench"


def test_matrix_verification_usages_match_scenario_identity_count(manifest: dict) -> None:
    for inc, count in SCENARIO_IDENTITY_COUNTS.items():
        entry = manifest["increments"][inc]
        assert len(entry["verification_usages"]) == count, inc


# ---------------------------------------------------------------------------
# --check mode
# ---------------------------------------------------------------------------

def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )


def test_check_mode_passes_on_current_repo() -> None:
    result = _run(["--check"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "passed" in result.stdout


def test_check_mode_detects_removal_via_diff(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Point the generator at a tampered tracked manifest and confirm --check
    # exits non-zero.
    tampered = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    tampered["increments"]["009F"]["scenario_identities"].remove("unavailableInput")
    tampered_path = tmp_path / "scenario-manifest.json"
    tampered_path.write_text(json.dumps(tampered, indent=2) + "\n", encoding="utf-8")

    monkeypatch.setattr(gen, "MANIFEST_PATH", tampered_path)
    assert gen.run_check() == 1


def test_tracked_manifest_matches_generator_output(tracked_manifest: dict) -> None:
    # The committed manifest must be exactly what the generator produces.
    assert tracked_manifest == gen.generate_manifest()
