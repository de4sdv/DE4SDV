"""Tests for scripts/check_model_sync.py — bidirectional model sync gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_model_sync.py"
MODEL_DIR = ROOT / "textual-notation-of-model/packages/features/aebs"

# Make scripts importable for unit-level checks.
sys.path.insert(0, str(ROOT))
from scripts import check_model_sync  # noqa: E402


def _run_script() -> subprocess.CompletedProcess[str]:
    """Run check_model_sync.py as a subprocess and return the result."""
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )


# ---------------------------------------------------------------------------
# End-to-end: script passes on the current repo
# ---------------------------------------------------------------------------


def test_script_passes_on_clean_repo():
    """The sync gate must pass on the current repository state."""
    result = _run_script()
    assert result.returncode == 0, (
        f"Expected exit 0, got {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "Model sync check passed." in result.stdout


# ---------------------------------------------------------------------------
# Unit-level: individual check functions return no errors on clean repo
# ---------------------------------------------------------------------------


def test_all_sync_points_pass_on_clean_repo():
    """Each check function must find no errors on the current repo."""
    errors = check_model_sync.run_all_checks()
    assert errors == [], f"Unexpected sync errors:\n{chr(10).join(errors)}"


def test_check_scenario_identities_clean():
    errors: list[str] = []
    check_model_sync.check_scenario_identities(errors)
    assert errors == []


def test_check_yaml_profiles_clean():
    errors: list[str] = []
    check_model_sync.check_yaml_profiles(errors)
    assert errors == []


def test_check_dependency_targets_clean():
    errors: list[str] = []
    check_model_sync.check_dependency_targets(errors)
    assert errors == []


def test_check_verification_usages_clean():
    errors: list[str] = []
    check_model_sync.check_verification_usages(errors)
    assert errors == []


# ---------------------------------------------------------------------------
# Deliberate breakage: scenario identity is detected
# ---------------------------------------------------------------------------


def test_broken_scenario_identity_detected():
    """Adding a bogus enum member to a SysML ScenarioIdentity must be caught."""
    sysml_file = MODEL_DIR / "aebs_override_verification.sysml"
    original = sysml_file.read_text(encoding="utf-8")

    # Inject a bogus member right after the opening brace of the enum.
    broken = original.replace(
        "enum def OverrideScenarioIdentity {",
        "enum def OverrideScenarioIdentity {\n    bogusNonExistentScenario;",
        1,
    )
    assert broken != original, "test setup: replacement did not alter the file"

    errors: list[str] = []
    with mock.patch.object(check_model_sync, "_read", side_effect=lambda p: broken if p == sysml_file else _read_original(p)):
        check_model_sync.check_scenario_identities(errors)

    assert errors, "Expected at least one error for broken scenario identity"
    assert any("SP1" in e for e in errors)


def _read_original(path: Path) -> str:
    """Helper: read the real file content from disk."""
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Deliberate breakage: dependency target is detected
# ---------------------------------------------------------------------------


def test_broken_dependency_target_detected():
    """A dependency pointing to a non-existent requirement must be caught."""
    sysml_file = MODEL_DIR / "aebs_override_verification.sysml"
    original = sysml_file.read_text(encoding="utf-8")

    # Replace the existing dependency target with a bogus one.
    broken = original.replace(
        "to reqAllowDriverOverride;",
        "to reqNonExistentBogusRequirement;",
        1,
    )
    assert broken != original, "test setup: replacement did not alter the file"

    errors: list[str] = []
    with mock.patch.object(check_model_sync, "_read", side_effect=lambda p: broken if p == sysml_file else _read_original(p)):
        check_model_sync.check_dependency_targets(errors)

    assert errors, "Expected at least one error for broken dependency target"
    assert any("reqNonExistentBogusRequirement" in e for e in errors)


# ---------------------------------------------------------------------------
# Helper function unit tests
# ---------------------------------------------------------------------------


def test_camel_to_snake():
    assert check_model_sync._camel_to_snake("freshFalseControl") == "fresh_false_control"
    assert check_model_sync._camel_to_snake("clearPath") == "clear_path"
    assert check_model_sync._camel_to_snake("staleInput") == "stale_input"
    assert check_model_sync._camel_to_snake("futureStampedOverride") == "future_stamped_override"


def test_names_correspond_exact():
    assert check_model_sync._names_correspond("stale_input", "stale_input")


def test_names_correspond_prefix():
    assert check_model_sync._names_correspond("stale_override", "stale")
    assert check_model_sync._names_correspond("stale", "stale_override")


def test_names_correspond_shared_first_word():
    assert check_model_sync._names_correspond(
        "fresh_true_override", "fresh_true_conscious_override"
    )


def test_names_correspond_no_match():
    assert not check_model_sync._names_correspond("bicycle", "pedestrian")
    assert not check_model_sync._names_correspond("stale_input", "malformed")


def test_check_member_correspondence_exact():
    assert check_model_sync._check_member_correspondence(
        ["a", "b"], ["a", "b"]
    ) is None


def test_check_member_correspondence_count_mismatch():
    result = check_model_sync._check_member_correspondence(["a", "b"], ["a"])
    assert result is not None
    assert "count" in result


def test_check_member_correspondence_no_match():
    result = check_model_sync._check_member_correspondence(
        ["apple", "banana"], ["cherry", "date"]
    )
    assert result is not None
    assert "apple" in result
