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
# Sync point 6: requirement-derivation coverage (ontology R003)
# ---------------------------------------------------------------------------

def test_check_requirement_derivation_coverage_clean():
    errors: list[str] = []
    check_model_sync.check_requirement_derivation_coverage(errors)
    assert errors == []


def _sp6_scenario(
    slice_text: str,
    kernel_text: str,
    tmp_path: Path,
):
    """Run sync point 6 against a synthetic kernel + slice; return errors.

    The kernel file provides the R003 origin groundings; the slice is the
    governed requirements slice under test. Model roots are pointed at the
    temporary directory so resolution covers exactly these two files.
    """
    kernel_path = tmp_path / "kernel.sysml"
    kernel_path.write_text(kernel_text, encoding="utf-8")
    slice_path = tmp_path / "slice.sysml"
    slice_path.write_text(slice_text, encoding="utf-8")

    grounding = {
        "Need": (str(kernel_path), "requirement def StakeholderNeedCandidate"),
        "RegulatoryConstraint": (
            str(kernel_path),
            "requirement def RegulatoryConstraintCandidate",
        ),
        "ArchitectureDecisionRecord": (
            str(kernel_path),
            "part def ArchitectureDecisionRecord",
        ),
    }
    errors: list[str] = []
    with mock.patch.object(
        check_model_sync, "_REQUIREMENT_SLICES", (slice_path,)
    ), mock.patch.object(
        check_model_sync, "_R003_MODEL_ROOTS", (tmp_path,)
    ), mock.patch.object(
        check_model_sync,
        "_load_ontology_r003_groundings",
        return_value=grounding,
    ):
        check_model_sync.check_requirement_derivation_coverage(errors)
    return errors


_SP6_KERNEL = """package K {
  requirement def StakeholderNeedCandidate { doc /* need grounding */ }
  requirement def RegulatoryConstraintCandidate { doc /* regulatory grounding */ }
  part def ArchitectureDecisionRecord { doc /* ADR grounding */ }
  requirement def ConcreteNeed :> StakeholderNeedCandidate { doc /* specialization */ }
  requirement def ConcreteReg :> RegulatoryConstraintCandidate { doc /* specialization */ }
  part def ConcreteAdr :> ArchitectureDecisionRecord { doc /* specialization */ }
}
"""


def _sp6_slice(dep_lines: str, extra_usages: str = "") -> str:
    return f"""package S {{
  requirement reqDesignInput : FunctionalRequirementCandidate {{
    doc /* design-input requirement under test */
  }}
  requirement needPeer : ConcreteNeed {{ doc /* peer need usage */ }}
  part adrPeer : ConcreteAdr {{ doc /* peer ADR usage */ }}
  requirement regPeer : ConcreteReg {{ doc /* peer regulatory usage */ }}
  part needFoo : DeferredProductLineScope {{ doc /* named need*, NOT a Need */ }}
  /* Peers carry valid derivations so the only variable is the dependency
   * under test. */
  dependency peerNeedDerivation from regPeer to needPeer;
  dependency peerAdrDerivation from regPeer to adrPeer;
  {extra_usages}
  {dep_lines}
}}
"""


def _sp6_flagged(errors: list[str], usage: str) -> bool:
    return any(f"'{usage}'" in error for error in errors)


def test_r003_requirement_to_need_passes(tmp_path: Path):
    errors = _sp6_scenario(
        _sp6_slice("dependency d1 from reqDesignInput to needPeer;"),
        _SP6_KERNEL,
        tmp_path,
    )
    assert errors == [], errors


def test_r003_requirement_to_regulatory_constraint_passes(tmp_path: Path):
    errors = _sp6_scenario(
        _sp6_slice("dependency d1 from reqDesignInput to regPeer;"),
        _SP6_KERNEL,
        tmp_path,
    )
    assert errors == [], errors


def test_r003_requirement_to_adr_passes(tmp_path: Path):
    errors = _sp6_scenario(
        _sp6_slice("dependency d1 from reqDesignInput to adrPeer;"),
        _SP6_KERNEL,
        tmp_path,
    )
    assert errors == [], errors


def test_r003_specialization_of_grounding_passes(tmp_path: Path):
    """Targets typed by specializations of the groundings also qualify."""
    slice_text = _sp6_slice(
        "dependency d1 from reqDesignInput to regPeer;",
        extra_usages=(
            "part adrSpecialization : ConcreteAdr { doc /* adr sub */ }\n"
            "  dependency d2 from regPeer to adrSpecialization;"
        ),
    )
    errors = _sp6_scenario(slice_text, _SP6_KERNEL, tmp_path)
    assert errors == [], errors


def test_r003_unrelated_target_fails(tmp_path: Path):
    """A derivation to an unrelated element does not satisfy R003."""
    errors = _sp6_scenario(
        _sp6_slice("dependency d1 from reqDesignInput to needFoo;"),
        _SP6_KERNEL,
        tmp_path,
    )
    assert _sp6_flagged(errors, "reqDesignInput"), errors


def test_r003_need_named_target_with_invalid_type_fails(tmp_path: Path):
    """A target named need* but not typed as Need is rejected (no prefixes)."""
    errors = _sp6_scenario(
        _sp6_slice(
            "dependency d1 from reqDesignInput to needFoo;",
            extra_usages=(
                "part needValidLooking : DeferredProductLineScope "
                "{ doc /* not a Need */ }"
            ),
        ),
        _SP6_KERNEL,
        tmp_path,
    )
    assert _sp6_flagged(errors, "reqDesignInput"), errors


def test_r003_deleted_sole_trace_fails(tmp_path: Path):
    """Deleting the only valid derivation fails the gate."""
    errors = _sp6_scenario(
        _sp6_slice("dependency d1 from reqDesignInput to adrPeerMissing;"),
        _SP6_KERNEL,
        tmp_path,
    )
    assert _sp6_flagged(errors, "reqDesignInput"), errors


def test_r003_retargeted_sole_trace_to_invalid_type_fails(tmp_path: Path):
    """Retargeting the only valid derivation to an invalid type fails."""
    # One valid trace deleted, replaced by a trace to an unrelated target.
    errors = _sp6_scenario(
        _sp6_slice(
            "dependency d1 from reqDesignInput to needFoo;\n"
            "  dependency d2 from needPeer to adrPeer;"
        ),
        _SP6_KERNEL,
        tmp_path,
    )
    assert _sp6_flagged(errors, "reqDesignInput"), errors


def test_r003_existing_aebs_model_passes_unchanged():
    """The committed AEBS/middleware slices satisfy the full R003 contract."""
    errors: list[str] = []
    check_model_sync.check_requirement_derivation_coverage(errors)
    assert errors == [], errors


def test_need_and_problem_statement_usages_are_out_of_scope(tmp_path: Path):
    """Stakeholder-need usages (typed by Need-grounding specializations) and
    the problem statement are not design-input requirements and must not
    require outgoing derivation links."""
    slice_text = """package S {
  requirement needSomething : ConcreteNeed {
    doc /* need usage without derivation; excluded semantically */
  }
  requirement framingStatement : ProblemStatement {
    doc /* problem statement without derivation; excluded */
  }
}
"""
    errors = _sp6_scenario(slice_text, _SP6_KERNEL, tmp_path)
    assert errors == [], errors


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
