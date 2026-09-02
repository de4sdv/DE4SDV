#!/usr/bin/env python3
"""Conservative naming/identity checks for DE4SDV (naming-conventions.md).

These checks encode only objective, low-risk rules from the authoritative
naming convention (docs/naming/naming-conventions.md):

- project-owned SysML filename shape;
- unexplained increment-number patterns in canonical concern filenames;
- registered identifier prefixes and subject namespaces for ID-shaped tokens;
- known generator output naming consistency for view diagrams.

Governed textual surface (documented in naming-conventions.md section 11):

- .sysml under the model roots — comment/doc/string content is scrubbed
  (SysML prose is not a governed identifier surface); code tokens are governed.
- .yaml/.yml under the governed areas — scanned RAW: identifiers inside
  normal scalar values, including quoted values, are governed data.
- .md — fenced code blocks are illustrative examples and are stripped;
  inline and prose text is governed.

Python sources are deliberately NOT token-scanned: they are executable
realizations whose literals include regex fragments and test fixtures that
are not governed identities (tests also deliberately contain invalid
examples). Governed identities in Python are covered by the migration guard
tests, not by this checker. This narrowing is normative documentation, not a
silent omission.

Named exclusions (never scanned): upstream/vendored libraries, snapshots,
synthetic fixtures, generated diagrams, retained-evidence directories,
immutable ADR history, and retained raw bench-evidence JSON records.

This checker validates syntax against the registries only. Retired grammar
families (E-, N-) are deterministically grandfathered: the exact existing
identity sets are enumerated in _GRANDFATHERED_IDENTITIES, those records
remain valid, and any sibling spelling under the retired grammar (e.g.
E-MW-999) is rejected like any unregistered prefix. Provenance rules that
cannot be enumerated (e.g. subject selection for new increments) remain
review policy.
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

# ---------------------------------------------------------------------------
# Governed textual surface for identifier scanning
# (naming-conventions.md section 11 — kept identical to the documentation)
# ---------------------------------------------------------------------------

GOVERNED_TEXT_AREAS = (
    "textual-notation-of-model/packages",
    "methodologies/sysmod-sysmlv2",
    "approach",
    "model-based-product-line-engineering",
    "implementation",
    "configuration-management",
    "continuous-homologation",
    "compliance",
    "devsecops",
    "simulation",
    "sysmlv2-api",
    "docs",
)

# Named exclusions from identifier scanning, each with a reason:
_EXEMPT_ID_PATH_PARTS = {
    "libraries",  # upstream/vendored Sysand libraries
    "snapshots",  # historical spike snapshots
    "fixture",  # synthetic fixture model area
    "fixtures",  # deliberate test-fixture locations
    "diagrams",  # generated SVG artifacts (names checked separately)
    "__pycache__",
}
_EXEMPT_PATH_PREFIXES = (
    # Retained evidence: historical records bound to evidence IDs.
    "implementation/aebs-aaos-sdv-visualization-bench/evidence/",
    "implementation/aaos-sdv-reference-interop-bench/evidence/",
    "implementation/aebs-autoware-nominal-vehicle-target-bench/evidence/",
    "implementation/aebs-autoware-stationary-target-bench/evidence/",
    # Immutable decision history (naming-conventions.md section 10).
    "docs/architecture-decisions/",
)
# Retained machine records whose token shapes are bench tooling, not DE4SDV IDs.
_EXEMPT_FILES = {
    "scenario-evidence.json",
    "run-metadata.json",
}

# Placeholder example artifacts (Status: draft/example, TBD rows): their IDs
# are illustrative template shapes, not governed records.
_EXAMPLE_TEMPLATE_FILES = {
    "compliance/safety/hazard-analysis-template.md",
    "compliance/security/threat-model-template.md",
    "continuous-homologation/evidence-register.md",
}

# Naming-authority docs quote unregistered forms as counterexamples and
# registry examples; their prose would otherwise self-flag. All three
# naming docs are exempt from token scanning — enforcement applies to the
# rest of the governed surface.
_EXEMPT_DOC_FILES = {
    "docs/naming/naming-conventions.md",
    "docs/naming/migration-manifest.md",
    "docs/naming/naming-qa-report.md",
    "docs/naming/model-organization-audit.md",
}

# Suffixes inside the governed surface. Python is intentionally excluded:
# governed IDs in Python are guarded by migration tests, and string scanning
# of Python produces regex-fragment false positives (naming-conventions.md
# section 11 documents this narrowing).
_GOVERNED_SUFFIXES = {".sysml", ".yaml", ".yml", ".md"}

# ---------------------------------------------------------------------------
# Identifier registry (docs/naming/naming-conventions.md section 5).
#
# STRICT_PREFIXES: `<TYPE>-<SUBJECT>-<SEQ>` trace IDs; the subject segment is
# validated against REGISTERED_SUBJECTS.
STRICT_PREFIXES = {
    "INC",
    "REQ",
    "NEED",
    "AC",
    "VC",
    "EVID",
    "GAP",
    "BL",
    "SC",
}

# Grandfathered identity sets: exact existing identities of retired grammars.
# New identities using these grammars are rejected deterministically; only
# the enumerated records below may still appear (naming-conventions.md §5.1).
#
# E-<SUBJECT>-<SEQ> (legacy evidence spelling) — superseded by EVID-.
# The retained set is the closed INC-MW-010 evidence chain referenced by
# middleware evidence records and the INC-AEBS-010 predecessor alignment;
# these identities are provenance-bearing and externally referenced.
_LEGACY_E_IDENTITIES = {
    "E-MW-008",
    "E-MW-010",
    "E-MW-011",
    "E-MW-012",
    "E-MW-013",
    "E-MW-014",
}

# N-<SUBJECT>-<SEQ> (legacy need spelling) — superseded by NEED- for new
# identities. Existing need records across AEBS 009-series benches, the
# middleware slice, and the AEBS operational-context pilot keep their
# identities (traceability anchors, evidence, bench configuration matrices).
_LEGACY_N_IDENTITIES = {
    "N-AEBS-001",
    "N-AEBS-002",
    "N-AEBS-003",
    "N-AEBS-004",
    "N-AEBS-005",
    "N-AEBS-006",
    "N-AEBS-007",
    "N-AEBS-008",
    "N-AEBS-009",
    "N-AEBS-010",
    "N-AEBS-011",
    "N-AEBS-012",
    "N-AEBS-013",
    "N-AEBS-014",
    "N-AEBS-OP-001",
    "N-AEBS-OP-002",
    "N-AEBS-OP-003",
    "N-AEBS-OP-004",
    "N-AEBS-OP-005",
    "N-MW-001",
    "N-MW-002",
    "N-MW-003",
    "N-MW-004",
    "N-MW-005",
    "N-MW-006",
    "N-MW-007",
    "N-MW-008",
    "N-MW-009",
}

_GRANDFATHERED_IDENTITIES = _LEGACY_E_IDENTITIES | _LEGACY_N_IDENTITIES

# FREE_FORM_PREFIXES: registered prefixes whose remainder is a free-form or
# tool-local name (role names, catalog records, bench identities, standard
# anchors). They must stay documented in the registry but their segments are
# not syntax-validated (no false positives on legitimate names).
FREE_FORM_PREFIXES = {
    "AO",  # acceptance objective (increment pilot index)
    "AGT",  # assurance argument (middleware evidence slice)
    "ASM",  # assumption (pilot index)
    "ACT",  # actor (pilot index)
    "ALT",  # realization alternative (pilot index)
    "BLK",  # physical element block (pilot index)
    "C",  # common capability node (feature model)
    "CAP",  # capability (pilot index)
    "CC",  # common capability (pilot index)
    "CCM",  # counter-claim (assurance argumentation)
    "CLS",  # classification record (pilot index)
    "CLM",  # claim (assurance argumentation)
    "D",  # derived asset (feature model)
    "DEC",  # decision record (pilot index)
    "DEF",  # deferral (pilot index)
    "EC",  # evidence criterion (pilot index)
    "F",  # feature node (feature model)
    "FEAT",  # feature (pilot index)
    "FUNC",  # function (pilot index)
    "ITEM",  # information item (pilot index)
    "LCOMP",  # logical component (pilot index)
    "LPORT",  # logical port (pilot index)
    "MAP",  # signal mapping record (pilot index)
    "MODEL",  # model artifact index entry (pilot index)
    "PL",  # product line (feature-model root)
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
    "VM",  # campaign bench virtual-machine host label
    "H",  # hazard (compliance safety template form)
    "T",  # threat (compliance security template form)
    "VP",  # viewpoint selection (pilot index)
    "VSS",  # VSS source/simulation mapping record
    "DE4SDV",  # DE4SDV project artifact reference (e.g. DE4SDV-VSS-EXT)
    "SYSML",  # external spec anchor (e.g. SYSML-V2-RELEASE-3f895b7)
    "SAF",  # external SAF anchor (e.g. SAF-CONCEPTUAL-DOMAIN)
    "UNECE",  # external regulation anchor (e.g. SRC-UNECE-R152 rest segment)
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
    # Technical vocabulary, not governed identifiers:
    "SHA-256",  # hash algorithm name (provenance records)
    "SHA-1",  # hash algorithm name (provenance records)
}

# Subject-first configuration identities (`<SUBJECT>-CONFIG-<SEQ>`); see
# naming-conventions.md section 5. `<SUBJECT>-` here is a registered subject
# namespace, so the generic strict-prefix scan would misread them.
_CONFIG_IDENTITY = re.compile(
    r"(?<![A-Za-z0-9-])(AEBS|MW)-CONFIG-[0-9]+(?:-[0-9]+)?\b"
)

# Subject-namespace registry (docs/naming/naming-conventions.md section 6).
# `UNECE` is the subject of SRC-UNECE-R152 (TYPE=SRC, SUBJECT=UNECE, REST=R152).
REGISTERED_SUBJECTS = {
    "AEBS",
    "MW",  # legacy registered code; canonical spelling is `middleware`
    "UNECE",
}

# ID-shaped token: PREFIX-SUBJECT(-...). Governed IDs are all-caps tokens
# whose subject segment (a) runs 3+ letters (AEBS, MW, UNKNOWN, PLATFORM,
# AEBS-010-…), (b) contains a digit (H-001, PF-004, AEBS-009B-01), or
# (c) is exactly 2 letters followed by another -segment (AC-MW-010-02,
# EVID-MW-011). Single-letter prose ranges (A-Z), mixed-case prose
# (SERVER-IPv4, AI-Ready), SPDX headers, and single-suffix bench labels
# (VM-A) stay outside the grammar by construction. The lookbehind prevents
# matching the tail of a longer ID (e.g. MW-010-02 inside AC-MW-010-02).
_ID_TOKEN = re.compile(
    r"(?<![A-Za-z0-9-])"
    r"([A-Z][A-Z0-9]{0,5})-"
    r"((?:[A-Z]{3,}[A-Z0-9]*(?:-[A-Z0-9]*)*"
    r"|[A-Z]{2}(?:-[A-Z0-9]+)+"
    r"|[A-Z]{0,2}[0-9][A-Z0-9-]*))"
)

# Markdown fenced code blocks: illustrative examples, outside enforcement
# (naming-conventions.md section 11). Inline code and prose stay governed.
_MD_FENCE = re.compile(r"```.*?```", re.DOTALL)

# Canonical concern filename: no embedded increment numbers.
_CONCERN_NUMBER = re.compile(r"_?0\d\d(_|\.sysml$)")

# Filenames that legitimately carry an increment identity (records).
_RECORD_EXEMPTIONS = {
    # Exact increment projections (identity-bearing records).
    "inc_aebs_009a_jetson_execution_environment.sysml",
}

# Upstream-named assets (never normalized): the SAF reference catalogue keeps
# its upstream-style filename; scans still include it for ID tokens.
_UPSTREAM_NAMED_FILES = {
    "textual-notation-of-model/packages/methods/saf/SAF_Viewpoints.sysml",
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


def _is_exempt_from_id_scan(path: Path) -> bool:
    parts = set(path.parts)
    if parts & _EXEMPT_SYSML_PATH_PARTS:
        return True
    rel = path.relative_to(ROOT).as_posix()
    if path.name in _EXEMPT_FILES:
        return True
    if rel in _EXAMPLE_TEMPLATE_FILES or rel in _EXEMPT_DOC_FILES:
        return True
    if rel == "docs/plans/2026-07-27-aebs-009c-009i.md":
        # Historical implementation-plan record; its title has used the
        # subjectless INC form verbatim since PR #68. History is not rewritten.
        return True
    if any(part in _EXEMPT_ID_PATH_PARTS for part in parts):
        return True
    return any(rel.startswith(prefix) for prefix in _EXEMPT_PATH_PREFIXES)


# Technical tokens that merely look like ID-shaped but are external
# vocabulary or URL fragments (never governed identifiers). The URL-pattern
# guard strips GitHub line-anchor suffixes such as `#L743-L754` before
# scanning. Extend deliberately, never silently — see naming-conventions.md
# section 5.
_URL_LINE_ANCHOR = re.compile(r"#L\d+(?:-L\d+)?")


def _prepare_text_for_suffix(text: str, suffix: str) -> str:
    """Artifact-aware preparation before ID scanning.

    - SysML: comments, doc blocks, and quoted strings are scrubbed (SysML
      prose is not a governed identifier surface; code tokens are).
    - Markdown: fenced code blocks are illustrative examples and are
      stripped; inline and prose text stays governed.
    - YAML (and everything else): returned raw — quoted scalar values ARE
      governed identifiers.
    """
    if suffix == ".sysml":
        text = _check_repo._scrub_comments_and_strings(text)
    elif suffix == ".md":
        text = _MD_FENCE.sub(" ", text)
    text = _URL_LINE_ANCHOR.sub(" ", text)
    text = _CONFIG_IDENTITY.sub("", text)
    for name in _EXTERNAL_ID_NAMES:
        text = text.replace(name, "")
    return text


def check_identifier_tokens_in_prepared(
    prepared_text: str, display_path: str
) -> list[str]:
    """Validate ID-shaped tokens in already-prepared text.

    Public seam: behavioral tests call this with fixture text to prove the
    observable checker behavior (registry enforcement), not regex internals.
    """
    errors: list[str] = []
    for match in _ID_TOKEN.finditer(prepared_text):
        prefix, rest = match.group(1), match.group(2)
        token = f"{prefix}-{rest}"
        if token in _GRANDFATHERED_IDENTITIES:
            # Grandfathered legacy identity: the exact record is retained;
            # sibling spellings (E-MW-999, N-MW-010) would not match and
            # fall through to normal validation below.
            continue
        if prefix in FREE_FORM_PREFIXES:
            continue
        if prefix not in STRICT_PREFIXES:
            errors.append(
                f"unregistered identifier prefix '{prefix}-' in {display_path}"
            )
            continue
        subject = rest.split("-", 1)[0]
        if subject not in REGISTERED_SUBJECTS:
            errors.append(
                f"unregistered identifier subject '{subject}' in {display_path}"
            )
    return errors


def check_identifier_tokens_in_text(
    text: str, display_path: str, suffix: str
) -> list[str]:
    """Prepare and validate one artifact's text (public behavioral seam)."""
    prepared = _prepare_text_for_suffix(text, suffix=suffix)
    return check_identifier_tokens_in_prepared(prepared, display_path=display_path)


def _iter_governed_text_files():
    for area in GOVERNED_TEXT_AREAS:
        base = ROOT / area
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in _GOVERNED_SUFFIXES:
                continue
            if _is_exempt_from_id_scan(path):
                continue
            yield path


def check_identifier_tokens() -> list[str]:
    """ID-shaped tokens in the governed textual surface must be registered.

    Artifact-aware preparation: SysML comments/strings scrubbed, YAML raw
    (quoted scalars governed), Markdown fenced examples stripped.
    """
    errors: list[str] = []
    for path in _iter_governed_text_files():
        text = path.read_text(errors="replace")
        prepared = _prepare_text_for_suffix(text, suffix=path.suffix)
        errors.extend(
            check_identifier_tokens_in_prepared(
                prepared, display_path=str(path.relative_to(ROOT))
            )
        )
    return errors


def check_sysml_filenames() -> list[str]:
    """Project-owned SysML filenames must be lower_snake_case and canonical."""
    errors: list[str] = []
    for root in SYSML_MODEL_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.sysml")):
            if _is_exempt_sysml(path):
                continue
            name = path.name
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
    errors.extend(check_sysml_filenames())
    errors.extend(check_identifier_tokens())
    errors.extend(check_view_diagram_names())
    return errors


def main() -> int:
    errors = run_all_checks()
    if errors:
        print("Naming check failed (docs/naming/naming-conventions.md):")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Naming check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
