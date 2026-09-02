#!/usr/bin/env python3
"""Conservative naming/identity checks for DE4SDV (naming-conventions.md).

These checks encode only objective, low-risk rules from the authoritative
naming convention (docs/naming/naming-conventions.md):

- project-owned SysML filename shape;
- unexplained increment-number patterns in canonical concern filenames;
- registered identifier prefixes and subject namespaces for ID-shaped tokens;
- known generator output naming consistency for view diagrams.

Everything ambiguous is exempted explicitly (with reasons) rather than
guessed. This checker never inspects upstream/vendor assets, retained
evidence, historical records, or deliberate fixtures.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

try:
    from scripts import check_repo as _check_repo
except ImportError:  # Direct execution from scripts/.
    import check_repo as _check_repo

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Governed locations
# ---------------------------------------------------------------------------

# Project-owned SysML model roots (filename-shape checks apply here only).
SYSML_MODEL_ROOTS = (
    ROOT / "textual-notation-of-model/packages",
    ROOT / "model-based-product-line-engineering/product-models",
)

# Directories whose SysML/asset names follow external or historical rules.
_EXEMPT_SYSML_PATH_PARTS = {
    "libraries",  # upstream/vendored Sysand libraries
    "snapshots",  # historical spike snapshots
    "fixture",  # synthetic test fixture models
}

# Identifier registry (docs/naming/naming-conventions.md section 5).
#
# STRICT_PREFIXES: `<TYPE>-<SUBJECT>-<SEQ>` trace IDs; the subject segment is
# validated against REGISTERED_SUBJECTS.
STRICT_PREFIXES = {
    "INC",
    "REQ",
    "N",
    "AC",
    "VC",
    "E",
    "EVID",
    "GAP",
    "BL",
    "SC",
}

# FREE_FORM_PREFIXES: registered prefixes whose remainder is a free-form or
# tool-local name (role names, catalog records, bench identities, standard
# anchors). They must stay documented in the registry but their segments are
# not syntax-validated (no false positives on legitimate names).
FREE_FORM_PREFIXES = {
    "AO",  # acceptance objective (increment pilot index)
    "ASM",  # assumption (pilot index)
    "ACT",  # actor (pilot index)
    "ALT",  # realization alternative (pilot index)
    "BLK",  # physical element block (pilot index)
    "CAP",  # capability (pilot index)
    "CC",  # common capability (pilot index)
    "CLS",  # classification record (pilot index)
    "DEC",  # decision record (pilot index)
    "DEF",  # deferral (pilot index)
    "EC",  # evidence criterion (pilot index)
    "FEAT",  # feature (pilot index)
    "FUNC",  # function (pilot index)
    "ITEM",  # information item (pilot index)
    "LCOMP",  # logical component (pilot index)
    "LPORT",  # logical port (pilot index)
    "MAP",  # signal mapping record (pilot index)
    "MODEL",  # model artifact index entry (pilot index)
    "PORT",  # port (pilot index)
    "PROBE",  # realization-readiness probe (pilot index)
    "PF",  # bench preflight check
    "QF",  # qualification finding (pilot index)
    "REAL",  # realization record (pilot index)
    "SCN",  # bench scenario identity
    "SET",  # needs/requirements set (pilot index)
    "SRC",  # external source anchor
    "STK",  # stakeholder index entry (pilot index)
    "STORY",  # operational story (pilot index)
    "VAL",  # validation scenario (pilot index)
    "VP",  # viewpoint selection (pilot index)
    "VSS",  # VSS source/simulation mapping record
    "DE4SDV",  # DE4SDV project artifact reference (e.g. DE4SDV-VSS-EXT)
    "SYSML",  # external spec anchor (e.g. SYSML-V2-RELEASE-3f895b7)
    "SAF",  # external SAF anchor (e.g. SAF-CONCEPTUAL-DOMAIN)
    "UNECE",  # external regulation anchor (e.g. UNECE-R152)
}

# External names that merely look like IDs (upstream projects/specs/tools).
# Extend deliberately, never silently — see naming-conventions.md section 5.
_EXTERNAL_ID_NAMES = {
    "S-CORE",
    "SAF-SysMLV2",
    "SAF-SysMLV2-DE4SDV",
    "SYSML-V2-SPEC-7",
    "MBSE4U-SYSMOD-PROBLEM-STATEMENT",
    "COVESA-VSS-VEHICLE-SPEED",
}

# Subject-first configuration identities (`<SUBJECT>-CONFIG-<SEQ>`); see
# naming-conventions.md section 5. `<SUBJECT>-` here is a registered subject
# namespace, so the generic strict-prefix scan would misread them.
_CONFIG_IDENTITY = re.compile(
    r"(?<![A-Z-])(AEBS|MW)-CONFIG-[0-9]+(?:-[0-9]+)?\b"
)

# Subject-namespace registry (docs/naming/naming-conventions.md section 6).
REGISTERED_SUBJECTS = {
    "AEBS",
    "MW",  # legacy registered code; canonical spelling is `middleware`
    "UNECE",
    "R152",  # UNECE R152 anchor uses SRC-UNECE-R152 form
}

# ID-shaped token: PREFIX-SUBJECT(-...). The lookbehind prevents matching the
# tail of a longer ID (e.g. MW-010-02 inside AC-MW-010-02, SDV-… inside
# DE4SDV-…).
_ID_TOKEN = re.compile(r"(?<![A-Za-z0-9-])([A-Z]{1,6})-([A-Z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*)")

# Files whose ID tokens are exempt (bench tooling / retained evidence).
_ID_EXEMPT_FILE_PARTS = {
    "scenario-evidence.json",
    "run-metadata.json",
}

# Canonical concern filename: no embedded increment numbers.
_CONCERN_NUMBER = re.compile(r"_?0\d\d(_|\.sysml$)")

# Filenames that legitimately carry an increment identity (records).
_RECORD_EXEMPTIONS = {
    # Exact increment projections (identity-bearing records).
    "inc_aebs_009a_jetson_execution_environment.sysml",
    # Historical retained-evidence slice is renamed to middleware_*; the
    # 010 in the package/file name is governed by the batch-2 manifest.
}

# Upstream-named assets (never normalized): the SAF reference catalogue keeps
# its upstream-style filename; scans still include it for ID tokens.
_UPSTREAM_NAMED_FILES = {
    "textual-notation-of-model/packages/methods/saf/SAF_Viewpoints.sysml",
}

# Batch-2 pending renames (documented in docs/naming/migration-manifest.md).
# These filenames still violate the convention; they are reported by the
# batch-2 checklist (tests/test_check_naming.py) rather than as repo errors
# so the current tree stays green until the scheduled migration executes.
_BATCH2_PENDING = {
    "aebs_010_visualization_framing.sysml",
    "aebs_010_visualization_functional_architecture.sysml",
    "aebs_010_visualization_logical_architecture.sysml",
    "aebs_010_visualization_needs_requirements.sysml",
    "aebs_010_visualization_operational_context.sysml",
    "aebs_010_visualization_physical_realization.sysml",
    "aebs_010_visualization_variability_configuration.sysml",
}

_REGISTERED_GENERATED_VIEWS = {
    "textual-notation-of-model/packages/features/aebs",
    "textual-notation-of-model/packages/features/middleware",
    "textual-notation-of-model/packages/architecture",
    "textual-notation-of-model/packages/methods/de4sdv",
    "model-based-product-line-engineering/product-models",
}

# diagram-<table|matrix>-> prefixes are inserted by artifact_filename().
_DIAGRAM_NAME = re.compile(r"^diagram-(?:(?:table|matrix)-)?([A-Za-z][A-Za-z0-9]*)\.svg$")


def _is_exempt_sysml(path: Path) -> bool:
    parts = set(path.parts)
    return bool(parts & _EXEMPT_SYSML_PATH_PARTS)


def check_sysml_filenames() -> tuple[list[str], list[str]]:
    """Project-owned SysML filenames must be lower_snake_case and canonical.

    Returns (errors, batch2_pending_advisories).
    """
    errors: list[str] = []
    batch2_pending: list[str] = []
    for root in SYSML_MODEL_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.sysml")):
            if _is_exempt_sysml(path):
                continue
            name = path.name
            if name in _BATCH2_PENDING:
                batch2_pending.append(str(path.relative_to(ROOT)))
                continue
            if str(path.relative_to(ROOT)) in _UPSTREAM_NAMED_FILES:
                continue
            if name != name.lower():
                errors.append(
                    f"SysML filename not lower_snake_case: {path.relative_to(ROOT)}"
                )
            if not re.fullmatch(r"[a-z][a-z0-9_]*\.sysml", name):
                errors.append(
                    f"SysML filename violates lower_snake_case grammar: "
                    f"{path.relative_to(ROOT)}"
                )
            if name not in _RECORD_EXEMPTIONS and _CONCERN_NUMBER.search(name):
                errors.append(
                    f"canonical concern filename embeds an increment number "
                    f"(naming-conventions.md section 7): {path.relative_to(ROOT)}"
                )
    return errors, batch2_pending


def check_identifier_tokens() -> list[str]:
    """ID-shaped tokens in tracked text must use registered prefixes/subjects."""
    errors: list[str] = []
    scan_roots = [
        ROOT / "textual-notation-of-model/packages",
        ROOT / "methodologies/sysmod-sysmlv2",
        ROOT / "tests",
        ROOT / "docs/naming",
    ]
    for root in scan_roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in {
                ".sysml", ".yaml", ".yml", ".py", ".md"
            }:
                continue
            if _is_exempt_sysml(path) or path.name in _ID_EXEMPT_FILE_PARTS:
                continue
            text = _check_repo._scrub_comments_and_strings(path.read_text())
            # _scrub_comments_and_strings is SysML-aware; for other files it
            # still removes quoted spans, which is the safe direction here.
            text = _CONFIG_IDENTITY.sub("", text)
            for name in _EXTERNAL_ID_NAMES:
                text = text.replace(name, "")
            for match in _ID_TOKEN.finditer(text):
                prefix, rest = match.group(1), match.group(2)
                if prefix in FREE_FORM_PREFIXES:
                    continue
                if prefix not in STRICT_PREFIXES:
                    errors.append(
                        f"unregistered identifier prefix '{prefix}-' in "
                        f"{path.relative_to(ROOT)}"
                    )
                    continue
                subject = rest.split("-", 1)[0]
                if subject not in REGISTERED_SUBJECTS:
                    errors.append(
                        f"unregistered identifier subject '{subject}' in "
                        f"{path.relative_to(ROOT)}"
                    )
    return errors


def check_view_diagram_names() -> list[str]:
    """Committed diagram names must be generator-consistent (no stale view ids)."""
    errors: list[str] = []
    try:
        from scripts import generate_view_index
    except ImportError:  # Direct execution from scripts/.
        import generate_view_index  # type: ignore
    for rel_dir in _REGISTERED_GENERATED_VIEWS:
        folder = ROOT / rel_dir
        diagrams = folder / "diagrams"
        if not diagrams.is_dir():
            continue
        try:
            collected = generate_view_index.collect_views(folder)
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(f"could not collect views for {rel_dir}: {exc}")
            continue
        expected = {
            generate_view_index.artifact_filename(spec.name, spec.view_type)
            for _, views in collected
            for spec in views
        }
        for svg in sorted(diagrams.glob("*.svg")):
            match = _DIAGRAM_NAME.match(svg.name)
            if not match:
                errors.append(f"unrecognized diagram filename: {svg.relative_to(ROOT)}")
                continue
            if svg.name not in expected:
                errors.append(
                    f"stale diagram name (no matching view identity): "
                    f"{svg.relative_to(ROOT)}"
                )
    return errors


def run_all_checks() -> list[str]:
    errors: list[str] = []
    filename_errors, batch2_pending = check_sysml_filenames()
    errors.extend(filename_errors)
    errors.extend(check_identifier_tokens())
    errors.extend(check_view_diagram_names())
    return errors


def batch2_pending_files() -> list[str]:
    """Advisory list: canonical-concern names awaiting the batch-2 migration."""
    _, batch2_pending = check_sysml_filenames()
    return batch2_pending


def main() -> int:
    errors = run_all_checks()
    batch2_pending = batch2_pending_files()
    if errors:
        print("Naming check failed (docs/naming/naming-conventions.md):")
        for error in errors:
            print(f"- {error}")
        return 1
    if batch2_pending:
        print(
            "Naming check passed with scheduled batch-2 renames pending "
            "(docs/naming/migration-manifest.md M11):"
        )
        for name in batch2_pending:
            print(f"- {name}")
        return 0
    print("Naming check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
