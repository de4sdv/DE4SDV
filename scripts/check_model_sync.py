#!/usr/bin/env python3
"""Consistency gates between SysML models and Python/YAML/test artifacts.

Checks repository contracts using text extraction from SysML textual notation:

1. Scenario identity enums: SysML ``enum def ScenarioIdentity009X`` members
   (camelCase → snake_case) must match Python evaluator enum values.
2. YAML profile names must match Python enum values.
3. Dependency traces in verification files must target real requirements
   defined in ``aebs_needs_requirements.sysml``.
4. Verification usages in each verification file must resolve to a
   ``verification def`` declared in the same file and must be performed.
5. The ontology-kernel contract must be complete in both directions: every
   ontology mapping resolves, and every governed kernel declaration is either
   mapped or explicitly excluded with a reason. Feature slices must not
   re-declare mapped kernel vocabulary.

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

# Verification .sysml files to scan (all increments).
VERIFICATION_SYSML_FILES = [
    "aebs_partial_intervention_verification.sysml",
    "aebs_override_verification.sysml",
    "aebs_non_activation_verification.sysml",
    "aebs_degraded_input_verification.sysml",
    "aebs_pedestrian_verification.sysml",
    "aebs_bicycle_verification.sysml",
    "aebs_regulatory_criterion_verification.sysml",
    "aebs_evidence.sysml",
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


# Sync point 5 — DE4SDV basic-ontology YAML ↔ method kernel declarations.
# The ontology YAML maps each class to the SysML declaration that carries its
# semantics. This gate verifies each mapped declaration still exists in the
# named kernel file, so the vocabulary cannot drift from the model unnoticed.
ONTOLOGY_YAML = ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"

# Native-mapping classes are validated separately (see check_ontology_kernel):
# their kernel mapping is "native", meaning the semantics live in a SysML v2
# language construct rather than a kernel declaration, or live in an external
# artifact outside the model (external).

# Helper and re-export declarations that appear in de4sdv_method_context.sysml
# but are not ontology vocabulary classes.
_ONTOLOGY_FILE_EXEMPT_DECLARATIONS: dict[str, set[str]] = {}


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
# Sync point 4: Verification usage ↔ def resolution and performance
# ---------------------------------------------------------------------------

_VERIFICATION_USAGE_RE = re.compile(
    r"\bverification\s+(\w+)\s*:\s*(\w+)\s*\{"
)
_VERIFICATION_DEF_RE = re.compile(r"\bverification\s+def\s+(\w+)")
_PERFORM_RE = re.compile(r"\bperform\s+(\w+)\s*;")


def check_verification_usages(errors: list[str]) -> None:
    """Sync point 4: usages resolve to local defs and are performed.

    Structural only: the exact set of usages per file is pinned by the
    generated scenario manifest (``generate_scenario_manifest.py --check``),
    so no hand-maintained expected-usages dict is needed here.
    """
    for sysml_name in VERIFICATION_SYSML_FILES:
        sysml_path = MODEL_DIR / sysml_name
        if not sysml_path.exists():
            errors.append(f"[SP4] {sysml_name}: file not found")
            continue
        code = _strip_comments(_read(sysml_path))
        defs = set(_VERIFICATION_DEF_RE.findall(code))
        usages = _VERIFICATION_USAGE_RE.findall(code)
        unresolved = sorted(
            {usage for usage, definition in usages if definition not in defs}
        )
        if unresolved:
            errors.append(
                f"[SP4] {sysml_name}: usages with no local verification def: "
                f"{unresolved}"
            )
        performed = set(_PERFORM_RE.findall(code))
        unperformed = sorted({usage for usage, _ in usages} - performed)
        if unperformed:
            errors.append(
                f"[SP4] {sysml_name}: verification usages never performed: "
                f"{unperformed}"
            )


# ---------------------------------------------------------------------------
# Ontology ↔ method-kernel contract
# ---------------------------------------------------------------------------

_ONTOLOGY_KERNEL = "[ONTOLOGY-KERNEL]"
FEATURES_DIR = ROOT / "textual-notation-of-model/packages/features"

# Match any one- or two-word SysML ``... def Name`` declaration kind at the
# start of a source line. This intentionally does not use a kind allowlist:
# new valid forms such as ``attribute def`` or ``connection def`` must enter
# the ontology-kernel inventory rather than silently escaping it.
_SYSML_DEFINITION_RE = re.compile(
    r"(?m)^[ \t]*"
    r"(?:(?:public|private|protected)[ \t]+)?"
    r"(?:abstract[ \t]+)?"
    r"([A-Za-z]+(?:[ \t]+[A-Za-z]+)?)[ \t]+def[ \t]+"
    r"([A-Za-z][A-Za-z0-9_]*)\b"
)

def _declaration_exists(sysml_text: str, declaration: str) -> bool:
    """Check that a declaration like 'part def X' or 'requirement def Y' exists.

    The declaration string is escaped into a regex; whitespace in it matches
    any whitespace run, and the name must appear as a whole word in
    comment-stripped text.
    """
    code = _strip_comments(sysml_text)
    pattern = r"\b" + re.escape(declaration).replace(r"\ ", r"\s+") + r"\b"
    return re.search(pattern, code) is not None


def _sysml_definitions(sysml_text: str) -> set[str]:
    """Return normalized ``<kind> def <name>`` declarations from SysML code."""
    code = _strip_comments(sysml_text)
    return {
        f"{' '.join(kind.split())} def {name}"
        for kind, name in _SYSML_DEFINITION_RE.findall(code)
    }


def _is_within(relative_file: str, relative_directory: str) -> bool:
    """Return whether one repository-relative path is inside a directory."""
    file_path = Path(relative_file)
    directory_path = Path(relative_directory)
    return (
        not file_path.is_absolute()
        and not directory_path.is_absolute()
        and ".." not in file_path.parts
        and ".." not in directory_path.parts
        and (file_path == directory_path or directory_path in file_path.parents)
    )


def check_ontology_kernel_contract(errors: list[str]) -> None:
    """Validate the bidirectional ontology ↔ SysML method-kernel contract.

    Each ontology class must carry a ``kernel`` mapping stating where its
    semantics live:

    - ``file:`` + ``declaration:`` — a SysML declaration in a kernel file;
      the gate verifies the declaration still exists there.
    - ``native:`` — the semantics live in a native SysML v2 language
      construct (no kernel declaration to check).
    - ``external:`` — the semantics live in an artifact outside the SysML
      model (feature catalogue, upstream library, evidence registers).

    The YAML ``kernel_sync`` block defines one governed method-kernel
    directory and explicit exclusions with reasons. Every declaration found
    in that directory must be either mapped by an ontology class or excluded;
    mappings and exclusions are compared as exact ``(file, declaration)``
    pairs. Feature slices may specialize/import mapped vocabulary but must not
    re-declare a mapped kernel name.
    """
    import yaml  # local import: PyYAML is a CI test dependency

    if not ONTOLOGY_YAML.exists():
        errors.append(f"{_ONTOLOGY_KERNEL} {ONTOLOGY_YAML}: ontology YAML not found")
        return

    try:
        doc = yaml.safe_load(_read(ONTOLOGY_YAML))
    except yaml.YAMLError as exc:
        errors.append(f"{_ONTOLOGY_KERNEL} {ONTOLOGY_YAML}: invalid YAML: {exc}")
        return

    classes = doc.get("classes") if isinstance(doc, dict) else None
    if not isinstance(classes, dict) or not classes:
        errors.append(f"{_ONTOLOGY_KERNEL} {ONTOLOGY_YAML}: no classes section")
        return

    contract = doc.get("kernel_sync")
    if not isinstance(contract, dict):
        errors.append(f"{_ONTOLOGY_KERNEL} {ONTOLOGY_YAML}: no kernel_sync contract")
        return
    governed_directory = contract.get("governed_directory")
    if not isinstance(governed_directory, str) or not governed_directory.strip():
        errors.append(
            f"{_ONTOLOGY_KERNEL} kernel_sync.governed_directory must be a "
            f"repository-relative directory"
        )
        return
    governed_directory = governed_directory.strip()
    governed_path = ROOT / governed_directory
    if (
        Path(governed_directory).is_absolute()
        or ".." in Path(governed_directory).parts
        or not governed_path.is_dir()
    ):
        errors.append(
            f"{_ONTOLOGY_KERNEL} governed kernel directory not found or unsafe: "
            f"{governed_directory}"
        )
        return

    raw_exclusions = contract.get("exclusions")
    if not isinstance(raw_exclusions, dict):
        errors.append(
            f"{_ONTOLOGY_KERNEL} kernel_sync.exclusions must map files to "
            f"excluded declarations and reasons"
        )
        return

    # Load each kernel file once.
    file_cache: dict[str, str] = {}
    mapped_pairs: set[tuple[str, str]] = set()
    for class_name, spec in classes.items():
        if not isinstance(spec, dict):
            errors.append(f"{_ONTOLOGY_KERNEL} {class_name}: malformed class entry")
            continue
        kernel = spec.get("kernel")
        if not isinstance(kernel, dict):
            errors.append(
                f"{_ONTOLOGY_KERNEL} {class_name}: missing kernel mapping "
                f"(file+declaration, native, or external)"
            )
            continue
        has_declaration = "file" in kernel or "declaration" in kernel
        has_native = "native" in kernel
        has_external = "external" in kernel
        if sum((has_declaration, has_native, has_external)) != 1:
            errors.append(
                f"{_ONTOLOGY_KERNEL} {class_name}: kernel mapping must use "
                f"exactly one of file+declaration, native, or external"
            )
            continue
        if has_declaration:
            rel_file = kernel.get("file")
            declaration = kernel.get("declaration")
            if (
                not isinstance(rel_file, str)
                or not rel_file.strip()
                or not isinstance(declaration, str)
                or not declaration.strip()
            ):
                errors.append(
                    f"{_ONTOLOGY_KERNEL} {class_name}: kernel mapping needs both "
                    f"file: and declaration: (got file={rel_file!r}, "
                    f"declaration={declaration!r})"
                )
                continue
            rel_file = rel_file.strip()
            declaration = declaration.strip()
            if Path(rel_file).is_absolute() or ".." in Path(rel_file).parts:
                errors.append(
                    f"{_ONTOLOGY_KERNEL} {class_name}: kernel file must be "
                    f"repository-relative: {rel_file}"
                )
                continue
            path = ROOT / rel_file
            if not path.exists():
                errors.append(
                    f"{_ONTOLOGY_KERNEL} {class_name}: kernel file not found: "
                    f"{rel_file}"
                )
                continue
            if rel_file not in file_cache:
                file_cache[rel_file] = _read(path)
            if not _declaration_exists(file_cache[rel_file], declaration):
                errors.append(
                    f"{_ONTOLOGY_KERNEL} {class_name}: declaration "
                    f"'{declaration}' not "
                    f"found in {rel_file}"
                )
            if _is_within(rel_file, governed_directory):
                mapped_pairs.add((rel_file, declaration))

    excluded_pairs: set[tuple[str, str]] = set()
    for rel_file, declarations in raw_exclusions.items():
        if not isinstance(rel_file, str) or not _is_within(
            rel_file, governed_directory
        ):
            errors.append(
                f"{_ONTOLOGY_KERNEL} exclusion file is outside the governed "
                f"directory or unsafe: {rel_file!r}"
            )
            continue
        if not isinstance(declarations, dict):
            errors.append(
                f"{_ONTOLOGY_KERNEL} exclusions for {rel_file} must map "
                f"declarations to reasons"
            )
            continue
        for declaration, reason in declarations.items():
            if not isinstance(declaration, str) or not declaration.strip():
                errors.append(
                    f"{_ONTOLOGY_KERNEL} {rel_file}: exclusion declaration "
                    f"must be a non-empty string"
                )
                continue
            if not isinstance(reason, str) or not reason.strip():
                errors.append(
                    f"{_ONTOLOGY_KERNEL} {rel_file}: exclusion "
                    f"'{declaration}' needs a non-empty reason"
                )
                continue
            excluded_pairs.add((rel_file, declaration.strip()))

    actual_pairs: set[tuple[str, str]] = set()
    for sysml_path in sorted(governed_path.rglob("*.sysml")):
        rel_file = str(sysml_path.relative_to(ROOT))
        for declaration in _sysml_definitions(_read(sysml_path)):
            actual_pairs.add((rel_file, declaration))

    for rel_file, declaration in sorted(actual_pairs - mapped_pairs - excluded_pairs):
        errors.append(
            f"{_ONTOLOGY_KERNEL} {rel_file}: declaration '{declaration}' is "
            f"unclassified; map it from an ontology class or add it to "
            f"kernel_sync.exclusions with a reason"
        )
    for rel_file, declaration in sorted(excluded_pairs - actual_pairs):
        errors.append(
            f"{_ONTOLOGY_KERNEL} {rel_file}: excluded declaration "
            f"'{declaration}' does not exist (stale exclusion?)"
        )
    for rel_file, declaration in sorted(mapped_pairs & excluded_pairs):
        errors.append(
            f"{_ONTOLOGY_KERNEL} {rel_file}: declaration '{declaration}' is "
            f"both ontology-mapped and excluded"
        )

    mapped_kernel_names = {declaration.split()[-1] for _, declaration in mapped_pairs}
    if FEATURES_DIR.is_dir():
        for sysml_path in sorted(FEATURES_DIR.rglob("*.sysml")):
            for declaration in _sysml_definitions(_read(sysml_path)):
                if declaration.split()[-1] in mapped_kernel_names:
                    rel_file = sysml_path.relative_to(ROOT)
                    errors.append(
                        f"{_ONTOLOGY_KERNEL} {rel_file}: feature slice "
                        f"re-declares mapped kernel name '{declaration.split()[-1]}'; "
                        f"specialize or import the kernel declaration instead"
                    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_all_checks() -> list[str]:
    """Run all repository model-sync contracts and return error strings."""
    errors: list[str] = []
    check_scenario_identities(errors)
    check_yaml_profiles(errors)
    check_dependency_targets(errors)
    check_verification_usages(errors)
    check_ontology_kernel_contract(errors)
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
