#!/usr/bin/env python3
"""Bidirectional consistency gate between SysML models and Python/YAML/test artifacts.

Checks four sync points using regex extraction from SysML textual notation:

1. Scenario identity enums: SysML ``enum def ScenarioIdentity009X`` members
   (camelCase → snake_case) must match Python evaluator enum values.
2. YAML profile names must match Python enum values.
3. Dependency traces in verification files must target real requirements
   defined in ``aebs_needs_requirements.sysml``.
4. Verification usage names must match the EXPECTED_USAGES dict in the test
   suite.

Exit code 0 on success, 1 on any mismatch.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "textual-notation-of-model/packages/features/aebs"
BENCH_SRC = (
    ROOT
    / "implementation/aebs-autoware-nominal-vehicle-target-bench"
    / "src/de4sdv_aebs_009b_bench/de4sdv_aebs_009b_bench"
)
CONFIG_DIR = (
    ROOT
    / "implementation/aebs-autoware-nominal-vehicle-target-bench/config"
)
NEEDS_FILE = MODEL_DIR / "aebs_needs_requirements.sysml"
TEST_USAGES_FILE = ROOT / "tests/test_aebs_009c_009i_verification_models.py"

# Verification .sysml files to scan (all increments).
VERIFICATION_SYSML_FILES = [
    "aebs_partial_intervention_verification.sysml",
    "aebs_override_verification.sysml",
    "aebs_non_activation_verification.sysml",
    "aebs_degraded_input_verification.sysml",
    "aebs_pedestrian_verification.sysml",
    "aebs_bicycle_verification.sysml",
    "aebs_regulatory_criterion_verification.sysml",
    "aebs_nominal_evidence.sysml",
]

# Sync point 1 — mapping of SysML scenario-identity enum to Python evaluator.
# (sysml_filename, python_filename, enum_class_name)
SCENARIO_IDENTITY_MAP: list[tuple[str, str, str]] = [
    (
        "aebs_override_verification.sysml",
        "override_matrix.py",
        "OverrideScenario",
    ),
    (
        "aebs_non_activation_verification.sysml",
        "non_activation_matrix.py",
        "NonActivationScenario",
    ),
    (
        "aebs_degraded_input_verification.sysml",
        "degraded_input_matrix.py",
        "DegradedInputScenario",
    ),
]

# Sync point 2 — YAML matrix configs to check against Python enums.
# (yaml_filename, python_filename, enum_class_name)
YAML_PROFILE_MAP: list[tuple[str, str, str]] = [
    (
        "scenario-009d-conscious-override-matrix.yaml",
        "override_matrix.py",
        "OverrideScenario",
    ),
    (
        "scenario-009e-non-activation-matrix.yaml",
        "non_activation_matrix.py",
        "NonActivationScenario",
    ),
    (
        "scenario-009f-degraded-input-matrix.yaml",
        "degraded_input_matrix.py",
        "DegradedInputScenario",
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _camel_to_snake(name: str) -> str:
    """Convert a camelCase identifier to snake_case."""
    s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()


def _strip_comments(text: str) -> str:
    """Remove /* */ and // comments from SysML text."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Sync point 1: Scenario identity enums
# ---------------------------------------------------------------------------

_SCENARIO_ENUM_RE = re.compile(
    r"enum\s+def\s+ScenarioIdentity(\w+)\s*\{([^}]*)\}", re.DOTALL
)


def _extract_scenario_identity_members(sysml_text: str) -> list[str] | None:
    """Extract camelCase member names from a ScenarioIdentity enum def.

    Returns ``None`` if the file has no such enum.
    """
    code = _strip_comments(sysml_text)
    match = _SCENARIO_ENUM_RE.search(code)
    if not match:
        return None
    body = match.group(2)
    return re.findall(r"\b([a-z][A-Za-z0-9]*)\s*;", body)


def _extract_python_enum_values(py_text: str, enum_class: str) -> list[str] | None:
    """Extract string values from a ``class X(str, Enum):`` block.

    Returns ``None`` if the class is not found.
    """
    class_pat = re.compile(
        rf"^class\s+{re.escape(enum_class)}\s*\([^)]*\)\s*:", re.MULTILINE
    )
    match = class_pat.search(py_text)
    if not match:
        return None
    # Start after the colon at the end of the class declaration line.
    lines = py_text[match.end():].split("\n")
    values: list[str] = []
    for line in lines:
        if line and not line[0].isspace():
            break
        m = re.match(r'\s+\w+\s*=\s*"([^"]+)"', line)
        if m:
            values.append(m.group(1))
    return values if values else None


def _names_correspond(sysml_snake: str, py_value: str) -> bool:
    """Check if a SysML snake_case name corresponds to a Python enum value.

    Accepts exact match, prefix match (one is a prefix of the other at a word
    boundary), or a shared first word when both names are multi-word.
    This handles intentionally divergent vocabularies like
    ``stale_override`` ↔ ``stale`` and ``fresh_true_override`` ↔
    ``fresh_true_conscious_override`` while still catching genuinely unrelated
    names.
    """
    if sysml_snake == py_value:
        return True
    # Prefix relationship at a word boundary.
    shorter, longer = sorted([sysml_snake, py_value], key=len)
    if longer.startswith(shorter) and (
        len(longer) == len(shorter) or longer[len(shorter)] == "_"
    ):
        return True
    # Shared first word (e.g. fresh_true_* on both sides).
    s_parts = sysml_snake.split("_")
    p_parts = py_value.split("_")
    return s_parts[0] == p_parts[0]


def _check_member_correspondence(
    sysml_members_snake: list[str], py_values: list[str],
) -> str | None:
    """Return an error string if the two lists don't correspond, else None.

    First tries exact set equality. If that fails, falls back to checking a
    one-to-one correspondence based on shared naming stems.
    """
    if set(sysml_members_snake) == set(py_values):
        return None

    if len(sysml_members_snake) != len(py_values):
        return (
            f"count mismatch: SysML has {len(sysml_members_snake)} members, "
            f"Python has {len(py_values)} values"
        )

    # Greedy one-to-one correspondence matching.
    unmatched_py = list(py_values)
    for member in sysml_members_snake:
        match = next(
            (v for v in unmatched_py if _names_correspond(member, v)),
            None,
        )
        if match is None:
            return (
                f"SysML member '{member}' has no corresponding Python value "
                f"in {sorted(py_values)}"
            )
        unmatched_py.remove(match)
    return None


def check_scenario_identities(errors: list[str]) -> None:
    """Sync point 1: SysML ScenarioIdentity members ↔ Python enum values."""
    for sysml_name, py_name, enum_class in SCENARIO_IDENTITY_MAP:
        sysml_path = MODEL_DIR / sysml_name
        py_path = BENCH_SRC / py_name

        members = _extract_scenario_identity_members(_read(sysml_path))
        if members is None:
            errors.append(
                f"[SP1] {sysml_name}: no ScenarioIdentity enum found"
            )
            continue

        values = _extract_python_enum_values(_read(py_path), enum_class)
        if values is None:
            errors.append(
                f"[SP1] {py_name}: enum class {enum_class} not found"
            )
            continue

        sysml_snake = [_camel_to_snake(m) for m in members]
        detail = _check_member_correspondence(sysml_snake, values)
        if detail is not None:
            errors.append(
                f"[SP1] {sysml_name} ↔ {py_name}::{enum_class}: {detail}\n"
                f"  SysML (snake_case): {sorted(sysml_snake)}\n"
                f"  Python values:      {sorted(values)}"
            )


# ---------------------------------------------------------------------------
# Sync point 2: YAML profile names ↔ Python enum values
# ---------------------------------------------------------------------------

_PROFILE_RE = re.compile(r"^\s+profile:\s*(\S+)\s*$", re.MULTILINE)


def _extract_yaml_profiles(yaml_text: str) -> list[str]:
    return _PROFILE_RE.findall(yaml_text)


def check_yaml_profiles(errors: list[str]) -> None:
    """Sync point 2: YAML profile values ↔ Python enum values."""
    for yaml_name, py_name, enum_class in YAML_PROFILE_MAP:
        yaml_path = CONFIG_DIR / yaml_name
        py_path = BENCH_SRC / py_name

        profiles = _extract_yaml_profiles(_read(yaml_path))
        values = _extract_python_enum_values(_read(py_path), enum_class)
        if values is None:
            errors.append(
                f"[SP2] {py_name}: enum class {enum_class} not found"
            )
            continue

        profile_set = set(profiles)
        value_set = set(values)

        if profile_set != value_set:
            errors.append(
                f"[SP2] {yaml_name} ↔ {py_name}::{enum_class}: mismatch\n"
                f"  YAML profiles:   {sorted(profile_set)}\n"
                f"  Python values:   {sorted(value_set)}\n"
                f"  In YAML not Py:  {sorted(profile_set - value_set)}\n"
                f"  In Py not YAML:  {sorted(value_set - profile_set)}"
            )


# ---------------------------------------------------------------------------
# Sync point 3: Dependency traces target real requirements
# ---------------------------------------------------------------------------

_DEP_TARGET_RE = re.compile(
    r"\bdependency\s+\w+\s*\n?\s*from\s+\w+\s+to\s+(req\w+|need\w+)\s*;",
    re.DOTALL,
)
_REQ_DEF_RE = re.compile(
    r"\brequirement\s+(req\w+|need\w+)\s*[:{]"
)


def _extract_requirement_names(needs_text: str) -> set[str]:
    """Extract all ``requirement reqXxx`` / ``requirement needXxx`` names."""
    code = _strip_comments(needs_text)
    return set(_REQ_DEF_RE.findall(code))


def _extract_dependency_targets(sysml_text: str) -> list[str]:
    """Extract ``to reqXxx`` / ``to needXxx`` targets from dependency lines."""
    code = _strip_comments(sysml_text)
    return _DEP_TARGET_RE.findall(code)


def check_dependency_targets(errors: list[str]) -> None:
    """Sync point 3: dependency targets must exist in aebs_needs_requirements."""
    req_names = _extract_requirement_names(_read(NEEDS_FILE))

    for sysml_name in VERIFICATION_SYSML_FILES:
        sysml_path = MODEL_DIR / sysml_name
        if not sysml_path.exists():
            continue
        targets = _extract_dependency_targets(_read(sysml_path))
        for target in targets:
            if target not in req_names:
                errors.append(
                    f"[SP3] {sysml_name}: dependency target '{target}' "
                    f"is not defined as a requirement in "
                    f"aebs_needs_requirements.sysml"
                )


# ---------------------------------------------------------------------------
# Sync point 4: Verification usage names ↔ EXPECTED_USAGES
# ---------------------------------------------------------------------------

_VERIFICATION_USAGE_RE = re.compile(
    r"\bverification\s+(\w+)\s*:\s*\w+\s*\{"
)


def _extract_expected_usages(test_text: str) -> dict[str, set[str]]:
    """Parse the EXPECTED_USAGES dict from the test file."""
    # Find the EXPECTED_USAGES = { ... } block.
    match = re.search(
        r"EXPECTED_USAGES\s*=\s*\{", test_text
    )
    if not match:
        return {}
    # Extract balanced braces.
    start = match.end() - 1  # position of opening {
    depth = 0
    end = start
    for i in range(start, len(test_text)):
        if test_text[i] == "{":
            depth += 1
        elif test_text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    block = test_text[start:end]

    result: dict[str, set[str]] = {}
    # Match increment keys: "009C": { ... }
    for inc_match in re.finditer(
        r'"(\d+[A-Z])"\s*:\s*\{([^}]*)\}', block
    ):
        inc = inc_match.group(1)
        body = inc_match.group(2)
        names = set(re.findall(r'"(\w+)"', body))
        result[inc] = names
    return result


# Map increment codes to verification .sysml filenames.
_INCREMENT_TO_FILE: dict[str, str] = {
    "009B": "aebs_nominal_evidence.sysml",
    "009C": "aebs_partial_intervention_verification.sysml",
    "009D": "aebs_override_verification.sysml",
    "009E": "aebs_non_activation_verification.sysml",
    "009F": "aebs_degraded_input_verification.sysml",
    "009G": "aebs_pedestrian_verification.sysml",
    "009H": "aebs_bicycle_verification.sysml",
    "009I": "aebs_regulatory_criterion_verification.sysml",
}


def check_verification_usages(errors: list[str]) -> None:
    """Sync point 4: verification usage names ↔ EXPECTED_USAGES in tests."""
    expected = _extract_expected_usages(_read(TEST_USAGES_FILE))
    if not expected:
        errors.append(
            f"[SP4] {TEST_USAGES_FILE.name}: could not parse EXPECTED_USAGES"
        )
        return

    for inc, expected_set in expected.items():
        sysml_name = _INCREMENT_TO_FILE.get(inc)
        if sysml_name is None:
            errors.append(f"[SP4] increment {inc}: no SysML file mapping")
            continue
        sysml_path = MODEL_DIR / sysml_name
        if not sysml_path.exists():
            errors.append(f"[SP4] {sysml_name}: file not found")
            continue
        code = _strip_comments(_read(sysml_path))
        actual = set(_VERIFICATION_USAGE_RE.findall(code))
        if actual != expected_set:
            errors.append(
                f"[SP4] {sysml_name} (inc {inc}): mismatch\n"
                f"  Expected:  {sorted(expected_set)}\n"
                f"  Actual:    {sorted(actual)}\n"
                f"  Missing:   {sorted(expected_set - actual)}\n"
                f"  Unexpected:{sorted(actual - expected_set)}"
            )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_all_checks() -> list[str]:
    """Run all four sync-point checks and return a list of error strings."""
    errors: list[str] = []
    check_scenario_identities(errors)
    check_yaml_profiles(errors)
    check_dependency_targets(errors)
    check_verification_usages(errors)
    return errors


def main() -> int:
    errors = run_all_checks()
    if errors:
        print("Model sync check FAILED.")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("Model sync check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
