#!/usr/bin/env python3
"""Generate the AEBS scenario manifest from SysML verification models.

The manifest makes the SysML model the canonical source for scenario
vocabulary: scenario identity enums, evidence outcome enums, and target type /
bench / verification definitions are extracted from the .sysml files and
emitted as a JSON document.

USAGE::

    python3 scripts/generate_scenario_manifest.py                  # print to stdout
    python3 scripts/generate_scenario_manifest.py --output PATH    # write to file
    python3 scripts/generate_scenario_manifest.py --check          # diff vs tracked manifest
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "textual-notation-of-model/packages/features/aebs"
MANIFEST_PATH = MODEL_DIR / "scenario-manifest.json"
SCHEMA = "de4sdv.scenario-manifest.v1"

# Ordered increment mapping: filename -> increment id.
INCREMENT_MAP: list[tuple[str, str]] = [
    ("aebs_evidence.sysml", "009B"),
    ("aebs_partial_intervention_verification.sysml", "009C"),
    ("aebs_override_verification.sysml", "009D"),
    ("aebs_non_activation_verification.sysml", "009E"),
    ("aebs_degraded_input_verification.sysml", "009F"),
    ("aebs_pedestrian_verification.sysml", "009G"),
    ("aebs_bicycle_verification.sysml", "009H"),
    ("aebs_regulatory_criterion_verification.sysml", "009I"),
]

# Increments whose target type (pedestrian / bicycle) is the distinguishing
# identity and which do not declare a ScenarioIdentity enum.
TARGET_TYPE_INCREMENTS = {"009G", "009H"}

# De-numbered semantic enum names per increment (model-organization-audit.md
# M3). INCREMENT_MAP keeps the filename -> increment provenance mapping; these
# registries map the increment to its slice's semantic enum type names.
SCENARIO_IDENTITY_ENUMS = {
    "009D": "OverrideScenarioIdentity",
    "009E": "NonActivationScenarioIdentity",
    "009F": "DegradedInputScenarioIdentity",
    "009I": "RegulatoryCriterionScenarioIdentity",
}
EVIDENCE_OUTCOME_ENUMS = {
    "009B": "NominalEvidenceOutcome",
    "009C": "PartialInterventionEvidenceOutcome",
    "009D": "OverrideEvidenceOutcome",
    "009E": "NonActivationEvidenceOutcome",
    "009F": "DegradedInputEvidenceOutcome",
    "009G": "PedestrianEvidenceOutcome",
    "009H": "BicycleEvidenceOutcome",
    "009I": "RegulatoryCriterionEvidenceOutcome",
}


# ---------------------------------------------------------------------------
# SysML text helpers
# ---------------------------------------------------------------------------

def _strip_comments(text: str) -> str:
    """Remove /* */ and // comments from SysML text."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _braced_body(source: str, after: int) -> tuple[str, int] | None:
    """Return (body, end_index) for the first { ... } block at/after ``after``.

    ``end_index`` is the index just past the closing brace.  Returns None when
    no brace block is found.
    """
    opening = source.find("{", after)
    if opening == -1:
        return None
    depth = 0
    for index in range(opening, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1:index], index + 1
    return None


def _find_declaration_body(source: str, declaration: str) -> str | None:
    """Return the inner body of ``declaration`` followed by a ``{ }`` block."""
    start = source.find(declaration)
    while start != -1:
        # Ensure the match is a whole token (not a suffix of a longer word).
        if start == 0 or not (source[start - 1].isalnum() or source[start - 1] == "_"):
            pair = _braced_body(source, start + len(declaration))
            if pair is not None:
                return pair[0]
        start = source.find(declaration, start + 1)
    return None


def _extract_enum_members(body: str) -> list[str]:
    """Extract camelCase enum members from an enum def body.

    Members are the identifiers on lines ending with ``;``.
    """
    members: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.endswith(";"):
            continue
        name = stripped[:-1].strip()
        # Allow only simple camelCase identifiers as members.
        if re.fullmatch(r"[a-z][A-Za-z0-9]*", name):
            members.append(name)
    return members


def _extract_enum(source: str, enum_name: str) -> tuple[str | None, list[str] | None]:
    """Find ``enum def <enum_name> { ... }`` and its members.

    Returns (enum_name, members) or (None, None) when the enum is absent.
    The enum names are the de-numbered semantic types introduced by the
    model-organization migration (model-organization-audit.md M3); the
    increment code stays recorded in INCREMENT_MAP provenance metadata.
    """
    declaration = f"enum def {enum_name}"
    body = _find_declaration_body(source, declaration)
    if body is None:
        return None, None
    return enum_name, _extract_enum_members(body)


def _extract_package_name(source: str) -> str | None:
    match = re.search(r"\bpackage\s+([A-Za-z_]\w*)", source)
    return match.group(1) if match else None


def _extract_verification_defs(source: str) -> list[str]:
    return re.findall(r"\bverification\s+def\s+(\w+)", source)


def _extract_verification_usages(source: str) -> list[str]:
    """``verification <usageName> :`` usage declarations."""
    return re.findall(r"\bverification\s+(\w+)\s*:\s*\w+", source)


def _extract_bench_definitions(source: str) -> list[str]:
    """``part def <BenchName>`` definitions (any part def, ordered)."""
    return re.findall(r"\bpart\s+def\s+(\w+)", source)


# ---------------------------------------------------------------------------
# Per-increment extraction
# ---------------------------------------------------------------------------

def _build_increment_entry(increment: str, sysml_file: str) -> dict:
    path = MODEL_DIR / sysml_file
    raw = path.read_text(encoding="utf-8")
    code = _strip_comments(raw)

    package_name = _extract_package_name(code)
    verification_defs = _extract_verification_defs(code)
    verification_usages = _extract_verification_usages(code)
    bench_defs = _extract_bench_definitions(code)

    scenario_enum, scenario_members = _extract_enum(
        code, SCENARIO_IDENTITY_ENUMS.get(increment, f"ScenarioIdentity{increment}")
    )
    outcome_enum, outcome_members = _extract_enum(
        code, EVIDENCE_OUTCOME_ENUMS.get(increment, f"EvidenceOutcome{increment}")
    )

    # Heuristic selection of the "primary" verification def and bench
    # definition. Prefer a name that contains both the increment code and a
    # distinguishing stem ("Bench" for benches), then fall back gracefully.
    primary_verification_def = next(
        (name for name in verification_defs if increment in name),
        verification_defs[0] if verification_defs else None,
    )
    primary_bench = (
        next((name for name in bench_defs if "Bench" in name and increment in name), None)
        or next((name for name in bench_defs if "Bench" in name), None)
        or next((name for name in bench_defs if increment in name), None)
        or (bench_defs[0] if bench_defs else None)
    )

    entry: dict = {
        "sysml_file": sysml_file,
        "package_name": package_name,
        "verification_def": primary_verification_def,
        "verification_usages": verification_usages,
        "scenario_identity_enum": scenario_enum,
        "evidence_outcome_enum": outcome_enum,
        "bench_definition": primary_bench,
    }
    if scenario_members is not None:
        entry["scenario_identities"] = scenario_members
    if outcome_members is not None:
        entry["evidence_outcomes"] = outcome_members
    if increment in TARGET_TYPE_INCREMENTS:
        # The target type (pedestrian/bicycle) is the distinguishing identity.
        target = "pedestrian" if increment == "009G" else "bicycle"
        entry["target_type"] = target
        entry["target_type_is_distinguishing_identity"] = True
    return entry


def generate_manifest() -> dict:
    """Build the full scenario manifest dict from the SysML models."""
    increments: dict[str, dict] = {}
    for sysml_file, increment in INCREMENT_MAP:
        increments[increment] = _build_increment_entry(increment, sysml_file)
    return {
        "schema": SCHEMA,
        "generated_from": "textual-notation-of-model/packages/features/aebs/",
        "increments": increments,
    }


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def _serialize(manifest: dict) -> str:
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def run_check() -> int:
    """Regenerate the manifest and diff against the tracked file.

    Returns 0 on match, 1 on drift (or missing tracked file).
    """
    errors = run_check_errors()
    if errors:
        for err in errors:
            print(err)
        return 1
    print("Scenario manifest check passed.")
    return 0


def run_check_errors() -> list[str]:
    """Return a list of error strings for manifest drift (empty = OK).

    Designed for integration into ``scripts/check_repo.py``, matching the
    convention of the other validators (return a list rather than printing).
    """
    if not MANIFEST_PATH.exists():
        return [
            "Scenario manifest not found: regenerate with "
            "`python3 scripts/generate_scenario_manifest.py --output "
            "textual-notation-of-model/packages/features/aebs/scenario-manifest.json`"
        ]
    regenerated = _serialize(generate_manifest())
    tracked = MANIFEST_PATH.read_text(encoding="utf-8")
    if regenerated != tracked:
        return [
            "Scenario manifest has drifted from the SysML models: regenerate with "
            "`python3 scripts/generate_scenario_manifest.py --output "
            "textual-notation-of-model/packages/features/aebs/scenario-manifest.json`"
        ]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the AEBS scenario manifest from SysML models.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the manifest to this path (default: print to stdout).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Regenerate and diff against the tracked manifest; exit 1 on drift.",
    )
    args = parser.parse_args(argv)

    if args.check:
        return run_check()

    manifest = generate_manifest()
    text = _serialize(manifest)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote manifest to {args.output}")
        return 0

    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
