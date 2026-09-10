#!/usr/bin/env python3
"""Consistency gates between SysML models and Python/YAML/test artifacts.

Checks repository contracts using text extraction from SysML textual notation:

1. Scenario identity enums: SysML scenario-identity enum members
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
6. Requirement-derivation coverage (ontology R003): every design-input
   requirement usage in a governed requirements slice must carry at least one
   outgoing dependency whose target resolves — through the model-wide
   declaration index and specialization closure — to a semantic type grounding
   Need, RegulatoryConstraint, or ArchitectureDecisionRecord. Identifier
   prefixes are never consulted; the permitted origin groundings are declared
   in the ontology's R003 ``origin_groundings`` block.

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

# Matches both the semantic scenario-identity enum names
# (<Scenario>ScenarioIdentity, model-organization-audit.md M3) and any legacy
# numbered spelling (ScenarioIdentity009X) for historical slices.
_SCENARIO_ENUM_RE = re.compile(
    r"enum\s+def\s+(?:[A-Za-z]+)?ScenarioIdentity(?:\w*)\s*\{([^}]*)\}", re.DOTALL
)


def _extract_scenario_identity_members(sysml_text: str) -> list[str] | None:
    """Extract camelCase member names from a ScenarioIdentity enum def.

    Returns ``None`` if the file has no such enum.
    """
    code = _strip_comments(sysml_text)
    match = _SCENARIO_ENUM_RE.search(code)
    if not match:
        return None
    body = match.group(1)
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


# ---------------------------------------------------------------------------
# Sync point 6: Requirement-derivation coverage (ontology R003)
# ---------------------------------------------------------------------------

# Design-input requirement slices in feature increments. R003 (basic-ontology
# validation_rules) requires every Requirement in a feature increment to trace
# to at least one Need, RegulatoryConstraint, or ArchitectureDecisionRecord.
# Evidence-contract slices are excluded: their requirement-like usages are
# System 2 planning vocabulary with a different trace obligation (trace to the
# controlled operational boundary), per REQ-AEBS-S2-001 and the ontology
# EvidenceContract mapping.
_REQUIREMENT_SLICES = (
    ROOT
    / "textual-notation-of-model/packages/features/aebs"
    / "aebs_needs_requirements.sysml",
    ROOT
    / "textual-notation-of-model/packages/features/aebs"
    / "aebs_visualization_needs_requirements.sysml",
    ROOT
    / "textual-notation-of-model/packages/features/middleware"
    / "middleware_requirements.sysml",
)

# Governed requirement usage: optional visibility modifier, unqualified or
# qualified type, body opened by ``{`` or terminated by ``;``. The type is
# captured including qualification, and a visibility modifier never removes
# a requirement from the governed population.
_REQUIREMENT_USAGE_RE = re.compile(
    r"^\s*(?:(?:public|private|protected)\s+)?requirement ([a-z][A-Za-z0-9]*)\s*:\s*"
    r"([A-Za-z][A-Za-z0-9_]*(?:::[A-Za-z][A-Za-z0-9_]*)*)"
    r"\s*(?:\{|;)",
    re.MULTILINE,
)
_DEPENDENCY_EDGE_RE = re.compile(
    r"^\s*(?:#[A-Za-z][A-Za-z0-9_]*\s+)?dependency\s+[A-Za-z][A-Za-z0-9]*\s+"
    r"from\s+([\w'.:]+)\s+to\s+([\w'.:]+)\s*;",
    re.MULTILINE | re.DOTALL,
)

# DE4SDV application derivation witnesses (plan v1.1 §16 final decision):
# `connection <name> : DerivesFromNeed connect <need> to <req>;`
# The first connector end is the `need` (StakeholderNeedCandidate lineage);
# the second is the `derivedRequirement` (RequirementCandidate lineage).
# Both ends must be requirement usages.
_DERIVATION_CONNECTION_RE = re.compile(
    r"^\s*connection\s+[A-Za-z][A-Za-z0-9]*\s*:\s*DerivesFromNeed\b"
    r"[^;]*?connect\s+([\w'.:]+)\s+to\s+([\w'.:]+)\s*;",
    re.MULTILINE | re.DOTALL,
)

# Model roots scanned to build the semantic type index used for R003 target
# resolution. This is deliberately the full governed model surface, not just
# the requirement slices, so a derivation may target a valid origin declared
# in another governed slice or in the method kernel.
_R003_MODEL_ROOTS = (
    ROOT / "textual-notation-of-model/packages",
    ROOT / "model-based-product-line-engineering/product-models",
    ROOT / "model-based-product-line-engineering/scoping",
)

# Matches ``<kind> def <Name> :> Parent1, Parent2 {`` — the specialization
# clause is optional. Only the declaration kind, name, and specialization
# parents are captured; bodies are irrelevant for type resolution.
_R003_DECLARATION_RE = re.compile(
    r"(?m)^[ \t]*"
    r"(?:(?:public|private|protected)[ \t]+)?"
    r"(?:abstract[ \t]+)?"
    r"([A-Za-z]+(?:[ \t]+[A-Za-z]+)?)[ \t]+def[ \t]+"
    r"([A-Za-z][A-Za-z0-9_]*)"
    r"(?:[ \t]*:>[ \t]*([A-Za-z][A-Za-z0-9_]*(?:::[A-Za-z][A-Za-z0-9_]*)*"
    r"(?:[ \t*,]+[A-Za-z][A-Za-z0-9_]*(?:::[A-Za-z][A-Za-z0-9_]*)*)*))?"
)

# Matches usage declarations ``<kind> <name> : <Type> {`` for the kinds that
# R003 origins can be modeled as (requirement usages and part usages). The
# declared type keeps its package qualification.
_R003_USAGE_RE = re.compile(
    r"(?m)^[ \t]*"
    r"(requirement|part|action)(?:[ \t]+(?:public|private|protected))?[ \t]+"
    r"([a-z][A-Za-z0-9_]*)[ \t]*:[ \t]*"
    r"([A-Za-z][A-Za-z0-9_]*(?:::[A-Za-z][A-Za-z0-9_]*)*)"
)

# Matches imports that bring names into a package scope. ``*`` imports make
# every member visible; named imports list specific members.
_IMPORT_RE = re.compile(
    r"(?m)^[ \t]*(?:public|private|protected)?[ \t]*import\s+"
    r"([A-Za-z][A-Za-z0-9_]*(?:::[A-Za-z][A-Za-z0-9_]*)*)"
    r"(::\*)?\s*;"
)

# Kind a semantic origin is declared with, per its kernel grounding kind.
_R003_ORIGIN_KINDS = {
    "requirement def",
    "part def",
}


class _R003ScopeError(RuntimeError):
    """A governed model text could not be resolved unambiguously (fail closed)."""


def _load_ontology_r003_groundings() -> dict[str, tuple[str, str]]:
    """Read the R003 origin groundings from the ontology YAML.

    The ontology owns the semantic mapping (R003 ``origin_groundings``);
    this gate only consumes it. Returns ``{origin_name: (file, declaration)}``.
    """
    import yaml  # local import: PyYAML is a CI test dependency

    doc = yaml.safe_load(_read(ONTOLOGY_YAML))
    rules = doc.get("validation_rules") or []
    for rule in rules:
        if isinstance(rule, dict) and rule.get("id") == "DE4SDV-ONT-R003":
            groundings = rule.get("origin_groundings")
            if not isinstance(groundings, dict) or not groundings:
                raise ValueError(
                    "ontology DE4SDV-ONT-R003 has no origin_groundings block"
                )
            result: dict[str, tuple[str, str]] = {}
            for origin, grounding in groundings.items():
                if not isinstance(grounding, dict):
                    raise ValueError(
                        f"R003 origin {origin!r} grounding must be a mapping"
                    )
                file_name = grounding.get("file")
                declaration = grounding.get("declaration")
                if not isinstance(file_name, str) or not isinstance(declaration, str):
                    raise ValueError(
                        f"R003 origin {origin!r} needs file+declaration grounding"
                    )
                result[origin] = (file_name, declaration)
            return result
    raise ValueError("ontology has no DE4SDV-ONT-R003 validation rule")


def _load_ontology_exclusion_groundings() -> dict[str, tuple[str, str]]:
    """Read the R003 exclusion groundings from the ontology YAML.

    Exclusion groundings name vocabulary that is traced INTO rather than out
    of (e.g. the kernel ProblemStatement). Returns
    ``{class_name: (file, declaration)}``; consumers must bind each class to
    declarations indexed from exactly that file, never to a bare name.
    """
    import yaml  # local import: PyYAML is a CI test dependency

    doc = yaml.safe_load(_read(ONTOLOGY_YAML))
    rules = doc.get("validation_rules") or []
    for rule in rules:
        if isinstance(rule, dict) and rule.get("id") == "DE4SDV-ONT-R003":
            groundings = rule.get("exclusion_groundings")
            if not isinstance(groundings, dict) or not groundings:
                raise ValueError(
                    "ontology DE4SDV-ONT-R003 has no exclusion_groundings block"
                )
            result: dict[str, tuple[str, str]] = {}
            for origin, grounding in groundings.items():
                if not isinstance(grounding, dict):
                    raise ValueError(
                        f"R003 exclusion {origin!r} grounding must be a mapping"
                    )
                file_name = grounding.get("file")
                declaration = grounding.get("declaration")
                if not isinstance(file_name, str) or not isinstance(declaration, str):
                    raise ValueError(
                        f"R003 exclusion {origin!r} needs file+declaration grounding"
                    )
                result[origin] = (file_name, declaration)
            return result
    raise ValueError("ontology has no DE4SDV-ONT-R003 validation rule")


def _r003_specialization_closure(
    declarations: dict[str, dict[str, object]],
    scope: dict[str, object],
    type_reference: str,
) -> set[str]:
    """Return the resolved type plus every type it (transitively) specializes.

    ``declarations`` maps qualified declaration names to records with a
    ``parents`` list of (possibly qualified) specialized type names. Every
    hop — the initial reference and each parent — is resolved through the
    referencing file's import ``scope``, so specializations declared in
    other packages (e.g. kernel groundings imported via ``::*``) resolve
    correctly. Unresolvable parents are ignored (they may be upstream
    library types outside the governed roots); ambiguous parents fail
    closed via :class:`_R003ScopeError`.
    """
    seen: set[str] = set()
    frontier = [_r003_resolve_type_reference(type_reference, scope)]
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        record = declarations.get(current)
        if record is None:
            continue
        for parent in record["parents"]:
            frontier.append(
                _r003_resolve_type_reference(str(parent), scope)
            )  # type: ignore[arg-type]
    return seen


def _r003_resolve_type_reference(
    reference: str,
    scope: "dict[str, object]",
) -> str:
    """Resolve a (possibly qualified) type reference to a qualified name.

    ``scope`` is a per-file resolution context produced by
    ``_r003_build_scope``. Resolution rules, in order:

    1. A fully qualified reference that exists in the declaration index is
       used as-is.
    2. Otherwise the reference is resolved through the file's import scope
       (exact import, ``::*`` import namespaces, then the referencing
       package's own namespace).
    3. A bare name that resolves to multiple candidates raises
       :class:`_R003ScopeError` — ambiguity fails closed instead of picking
       an arbitrary homonym.
    """
    candidates: list[str] = []
    if reference in scope["declarations"]:  # type: ignore[operator]
        return reference
    for prefix in scope["visible_namespaces"]:  # type: ignore[operator]
        qualified = f"{prefix}::{reference}"
        if qualified in scope["declarations"]:  # type: ignore[operator]
            candidates.append(qualified)
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise _R003ScopeError(
            f"ambiguous reference '{reference}' resolves to "
            + ", ".join(sorted(candidates))
        )
    # Undeclared reference (e.g. an upstream library type): keep the bare
    # name so the closure simply cannot resolve it — no valid origin.
    return reference


def _r003_build_scope(
    package_path: str,
    code: str,
    declarations: dict[str, dict[str, object]],
) -> dict[str, object]:
    """Build the import-resolution scope for one governed file.

    ``package_path`` is the dotted name of the package that owns the
    requirement slice (the outermost ``package`` in the file). Wildcard
    imports make every member of the imported namespace visible; named
    imports make the imported namespace itself visible.
    """
    visible: list[str] = []
    for namespaced, wildcard in _IMPORT_RE.findall(code):
        if wildcard:
            visible.append(namespaced)
        else:
            visible.append(namespaced.rsplit("::", 1)[0])
    if package_path:
        visible.append(package_path)
    return {
        "declarations": declarations,
        "visible_namespaces": visible,
    }


def _r003_outermost_package(code: str) -> str:
    match = re.search(r"(?m)^\s*package\s+([A-Za-z][A-Za-z0-9_]*)\s*\{", code)
    return match.group(1) if match else ""


def _r003_nested_package_prefixes(code: str) -> list[str]:
    """Dotted package prefixes for every nested ``package`` block in a file.

    Returns prefixes outermost-first, e.g. ``Pkg``, ``Pkg::Features``,
    ``Pkg::Features::AEBS``. Uses brace-depth scanning on comment-stripped
    code; body braces of declarations are irrelevant because only
    ``package <Name> {`` lines extend the prefix.
    """
    prefixes: list[str] = []
    stack: list[str] = []
    pattern = re.compile(
        r"(?m)^[ \t]*package\s+([A-Za-z][A-Za-z0-9_]*)\s*\{"
    )
    events: list[tuple[int, int]] = []  # (position, +1 open / -1 close)
    open_positions: dict[int, str] = {}
    for match in pattern.finditer(code):
        open_positions[match.end() - 1] = match.group(1)
    depth_delta = []
    opens = {pos: name for pos, name in open_positions.items()}
    for index, char in enumerate(code):
        if char == "{":
            depth_delta.append((index, 1))
        elif char == "}":
            depth_delta.append((index, -1))
    depth = 0
    for position, delta in depth_delta:
        if delta == 1 and position in opens:
            stack.append(opens[position])
            prefixes.append("::".join(stack))
        depth += delta
        if delta == -1 and stack and depth < len(stack):
            stack.pop()
    return prefixes


def _r003_name_declared_in_block(code: str, prefix: str, name: str) -> bool:
    """True when ``name`` is declared directly inside the ``prefix`` block.

    Single pass over every brace: each ``{`` pushes a frame; a ``package``
    header names the frame it opens; each ``}`` pops exactly one frame.
    Package spans are recorded from header frames only, so requirement and
    doc bodies keep the depth balanced and sibling/nested packages resolve
    to their true dotted prefixes.
    """
    header_pattern = re.compile(
        r"^[ \t]*package\s+([A-Za-z][A-Za-z0-9_]*)[ \t]*\{",
        re.MULTILINE,
    )
    declaration_pattern = re.compile(
        r"^[ \t]*(?:requirement|part|action)[ \t]+(?:def[ \t]+)?"
        + re.escape(name)
        + r"(?:::)?[ \t]*[:{;]",
        re.MULTILINE,
    )
    wanted = tuple(prefix.split("::"))

    headers = {match.end() - 1: match.group(1) for match in header_pattern.finditer(code)}
    frames: list[tuple[str | None, int]] = []  # (header name, body_start)
    spans: list[tuple[tuple[str, ...], int, int]] = []
    for index, char in enumerate(code):
        if char == "{":
            frames.append((headers.get(index), index + 1))
        elif char == "}":
            if not frames:
                continue
            header_name, body_start = frames.pop()
            if header_name is not None:
                prefix_names = tuple(
                    entry[0] for entry in frames if entry[0] is not None
                ) + (header_name,)
                spans.append((prefix_names, body_start, index))
    for span_prefix, span_start, span_end in spans:
        if span_prefix == wanted:
            return bool(declaration_pattern.search(code[span_start:span_end]))
    return False

def check_requirement_derivation_coverage(errors: list[str]) -> None:
    """Sync point 6: every design-input requirement traces to a valid R003 origin.

    Enforces ontology validation rule DE4SDV-ONT-R003 against the model text:
    each requirement usage in a governed requirements slice must carry at least
    one outgoing dependency whose target resolves — through qualified
    declaration/usage indexes, per-file import scopes, and specialization
    closure — to a semantic type grounding one of the permitted origin types
    (Need, RegulatoryConstraint, ArchitectureDecisionRecord). Identifier
    prefixes are never consulted: a target named ``needFoo`` that is not
    typed as a Need is rejected, and ambiguous references fail closed.
    This checks presence of the required link (the gap the dependency-target
    check cannot see); semantic strength of each link remains review policy.
    """
    groundings = _load_ontology_r003_groundings()

    # Model-wide indexes keyed by QUALIFIED declaration name (kind is part of
    # the identity so a part def and a requirement def with the same name do
    # not collide) plus a global usage registry keyed by bare name whose
    # values carry every (qualified identity, declared type, owning file)
    # triple. Identities — not guesses — drive resolution; ambiguity in any
    # consumed lookup fails closed.
    declarations: dict[str, dict[str, object]] = {}
    declarations_by_name: dict[str, list[str]] = {}
    usages: dict[str, list[tuple[str, str, Path]]] = {}
    scopes: dict[Path, dict[str, object]] = {}
    for model_root in _R003_MODEL_ROOTS:
        if not model_root.is_dir():
            continue
        for path in sorted(model_root.rglob("*.sysml")):
            raw_code = _read(path)
            code = _strip_comments(raw_code)
            package_path = _r003_outermost_package(code)
            scope = _r003_build_scope(package_path, code, declarations)
            scopes[path] = scope
            for kind, name, parents in _R003_DECLARATION_RE.findall(code):
                qualified = f"{package_path}::{name}" if package_path else name
                parent_list = [
                    parent.strip().rstrip(",")
                    for parent in (parents or "").split(",")
                    if parent.strip().rstrip(",")
                ]
                declarations[qualified] = {
                    "kind": " ".join(kind.split()),
                    "parents": parent_list,
                    "file": str(path),
                }
                declarations_by_name.setdefault(name, []).append(qualified)
            # Usage identities include the file's nested ``package`` structure
            # so a qualified dependency target matches the declaration site.
            nesting = _r003_nested_package_prefixes(code)
            for usage_kind, usage_name, usage_type in _R003_USAGE_RE.findall(code):
                identity = usage_name
                for prefix in sorted(nesting, key=lambda p: p.count("::"), reverse=True):
                    if _r003_name_declared_in_block(code, prefix, usage_name):
                        identity = f"{prefix}::{usage_name}"
                        break
                usages.setdefault(usage_name, []).append(
                    (identity, usage_type, path)
                )

    # Grounding declarations must exist and carry a permitted kind.
    origin_qualified: set[str] = set()
    origin_bare: set[str] = set()
    for origin, (file_name, declaration) in groundings.items():
        if not _declaration_exists(_read(ROOT / file_name), declaration):
            errors.append(
                f"[SP6] ontology R003 origin {origin!r} grounding declaration "
                f"'{declaration}' not found in {file_name}"
            )
            continue
        kind, _, grounding_name = declaration.partition(" def ")
        if f"{kind} def" not in _R003_ORIGIN_KINDS:
            errors.append(
                f"[SP6] ontology R003 origin {origin!r} grounding "
                f"'{declaration}' is not a supported requirement/part def"
            )
            continue
        origin_bare.add(grounding_name)
        grounding_file = str(ROOT / file_name)
        # Identity, not a bare-name homonym: only declarations indexed from
        # the grounding's own file may satisfy this origin.
        grounded_qualifications = [
            qualified
            for qualified in declarations_by_name.get(grounding_name, [])
            if declarations[qualified].get("file") == grounding_file
        ]
        if grounded_qualifications:
            origin_qualified.update(grounded_qualifications)
        else:
            # Kernel file not under the scanned roots (e.g. a synthetic test
            # kernel): the bare name is the only identity available.
            origin_qualified.add(grounding_name)

    # The kernel file declares groundings; ensure the grounding declarations
    # themselves are indexed (they live inside the method-kernel package).
    kernel_paths = {
        ROOT / file_name for file_name, _ in groundings.values()
    }
    for kernel_path in kernel_paths:
        if not kernel_path.exists() or kernel_path in scopes:
            continue
        code = _strip_comments(_read(kernel_path))
        package_path = _r003_outermost_package(code)
        scope = _r003_build_scope(package_path, code, declarations)
        scopes[kernel_path] = scope
        for kind, name, parents in _R003_DECLARATION_RE.findall(code):
            qualified = f"{package_path}::{name}" if package_path else name
            parent_list = [
                parent.strip().rstrip(",")
                for parent in (parents or "").split(",")
                if parent.strip().rstrip(",")
            ]
            declarations[qualified] = {
                "kind": " ".join(kind.split()),
                "parents": parent_list,
                "file": str(kernel_path),
            }
            declarations_by_name.setdefault(name, []).append(qualified)
        if package_path:
            origin_qualified.update(
                f"{package_path}::{name}"
                for name in origin_bare
                if f"{package_path}::{name}" in declarations
            )

    exclusion_groundings = _load_ontology_exclusion_groundings()
    ps_file, ps_declaration = exclusion_groundings["ProblemStatement"]
    ps_grounding_name = ps_declaration.partition(" def ")[2]
    ps_grounding_file = str(ROOT / ps_file)
    problem_statement_qualified = {
        qualified
        for qualified in declarations_by_name.get(ps_grounding_name, [])
        if declarations[qualified].get("file") == ps_grounding_file
    }
    if not problem_statement_qualified:
        errors.append(
            f"[SP6] ProblemStatement exclusion grounding '{ps_declaration}' "
            f"is not indexed from {ps_file}"
        )

    def _closure_hits(
        scope: dict[str, object],
        reference: str,
        allowed: set[str],
    ) -> bool:
        try:
            closure = _r003_specialization_closure(declarations, scope, reference)
        except _R003ScopeError as error:
            raise _R003ScopeError(f"[SP6] {error}") from error
        return any(name in allowed for name in closure)

    def _usage_entries_for_target(
        target: str,
        slice_file: Path,
        slice_prefixes: tuple[str, ...],
    ) -> tuple[list[tuple[str, str, Path]], list[str]]:
        """Registry entries matching the written target, plus ambiguities.

        Matching rules, in order:

        1. A qualified reference matches by SEGMENT identity: exact
           identity, full suffix identity (``identity.endswith("::" +
           reference)``), or trailing-segment match (the identity's last
           ``len(reference segments)`` segments equal the reference's
           segments — SysML visibility may let a writer omit leading
           packages). Differently typed candidates are reported as
           ambiguous and fail closed. String prefix matching is never
           used: ``Bad::origin`` cannot match ``BadExtra::origin``.
        2. A bare reference resolves only within the referencing slice's
           lexical scope: usages declared in the slice file inside the
           slice's package chain. An unrelated same-named usage in another
           package can never be borrowed. Divergent types in scope are
           ambiguous (fail closed).
        """
        reference = target.strip("'")
        bare = reference.rsplit("::", 1)[-1]
        entries = usages.get(bare, [])
        if not entries:
            return [], []
        if "::" in reference:
            ref_segments = reference.split("::")
            exact = [
                entry
                for entry in entries
                if entry[0] == reference or entry[0].endswith("::" + reference)
            ]
            if exact:
                return exact, []
            def _segments_in_order(needle: list[str], hay: list[str]) -> bool:
                iterator = iter(hay)
                return all(segment in iterator for segment in needle)

            partial = [
                entry
                for entry in entries
                if len(ref_segments) >= 2
                and entry[0].endswith("::" + ref_segments[-1])
                and _segments_in_order(
                    ref_segments[:-1],
                    entry[0].split("::")[:-1],
                )
            ]
            if not partial:
                return [], []
            types = {entry[1] for entry in partial}
            if len(types) > 1:
                identities = ", ".join(sorted(entry[0] for entry in partial))
                return [], [
                    f"ambiguous derivation target '{reference}' matches "
                    f"distinctly typed usages: {identities}"
                ]
            return partial, []
        visible = [
            entry
            for entry in entries
            if entry[2] == slice_file
            and (
                entry[0] == bare
                or entry[0].rsplit("::", 1)[0] in slice_prefixes
            )
        ]
        if not visible:
            return [], []
        types = {entry[1] for entry in visible}
        if len(types) > 1:
            identities = ", ".join(sorted(entry[0] for entry in visible))
            return [], [
                f"ambiguous derivation target '{reference}' matches "
                f"distinctly typed usages in scope: {identities}"
            ]
        return visible, []

    def _resolves_to_valid_origin(
        scope: dict[str, object],
        target: str,
        slice_file: Path,
        slice_prefixes: tuple[str, ...],
    ) -> bool:
        entries, ambiguities = _usage_entries_for_target(
            target, slice_file, slice_prefixes
        )
        if ambiguities:
            raise _R003ScopeError(f"[SP6] {ambiguities[0]}")
        for _identity, usage_type, owner_path in entries:
            owner_scope = scopes.get(owner_path, scope)
            if _closure_hits(owner_scope, usage_type, origin_qualified):
                return True
        reference = target.strip("'")
        # A qualified target may itself be a declaration (e.g. a kernel
        # grounding usage written qualified) rather than a registry usage.
        # Bare names are never treated as global declarations.
        if "::" in reference:
            return _closure_hits(scope, reference, origin_qualified)
        return False

    for slice_path in _REQUIREMENT_SLICES:
        if not slice_path.exists():
            errors.append(
                f"[SP6] {slice_path.name}: requirements slice not found"
            )
            continue
        code = _strip_comments(_read(slice_path))
        if slice_path not in scopes:
            scopes[slice_path] = _r003_build_scope(
                _r003_outermost_package(code), code, declarations
            )
        scope = scopes[slice_path]
        slice_prefixes = tuple(_r003_nested_package_prefixes(code))
        usages_in_slice = set(_REQUIREMENT_USAGE_RE.findall(code))
        edges = _DEPENDENCY_EDGE_RE.findall(code)
        # DE4SDV DerivesFromNeed application connections: the first
        # connector end is the `need`, the second the `derivedRequirement`.
        # An outgoing derivation from a requirement to a need is the inverse
        # traversal of that native witness (plan v1.1 §16).
        edges += [
            (derived, original)
            for original, derived in _DERIVATION_CONNECTION_RE.findall(code)
        ]
        need_grounding_name = groundings["Need"][1].partition(" def ")[2]
        need_qualified = {
            qualified
            for qualified in declarations_by_name.get(need_grounding_name, [])
        } or {need_grounding_name}
        for usage_name, usage_type in sorted(usages_in_slice):
            # Semantic exclusions — resolved types, never suffixes:
            # 1. A usage whose type specializes the Need grounding is itself
            #    a stakeholder need, not a design-input requirement.
            # 2. A usage whose type specializes the kernel ProblemStatement
            #    grounding (bound to its ontology-declared file) is framing
            #    vocabulary traced INTO, not out of.
            try:
                if _closure_hits(scope, usage_type, need_qualified):
                    continue
                if _closure_hits(
                    scope, usage_type, problem_statement_qualified
                ):
                    continue
            except _R003ScopeError as error:
                errors.append(f"{error} (while excluding {usage_name!r})")
                continue
            valid_targets = []
            failed_closed = False
            for source, target in edges:
                if source != usage_name:
                    continue
                try:
                    if _resolves_to_valid_origin(
                        scope, target, slice_path, slice_prefixes
                    ):
                        valid_targets.append(target)
                except _R003ScopeError as error:
                    errors.append(str(error))
                    failed_closed = True
                    break
            if failed_closed:
                continue
            if not valid_targets:
                errors.append(
                    f"[SP6] {slice_path.name}: requirement usage '{usage_name}' "
                    f"({usage_type}) has no outgoing derivation dependency to a "
                    f"Need, RegulatoryConstraint, or ArchitectureDecisionRecord "
                    f"(ontology rule DE4SDV-ONT-R003)"
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
    check_requirement_derivation_coverage(errors)
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
