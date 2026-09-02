"""Behavioral tests for scripts/check_naming.py — naming/identity checks.

These tests exercise the PUBLIC checker behavior (check_identifier_tokens_in_text
over prepared fixture text, plus the real repository surface via
check_identifier_tokens), not private regex internals. The registry contract
lives in docs/naming/naming-conventions.md; these tests pin that the
documented and executable grammars are identical and that invalid identifiers
cannot silently pass through quoted/project-owned textual artifacts.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import check_naming  # noqa: E402


# ---------------------------------------------------------------------------
# Public seams
# ---------------------------------------------------------------------------


def _yaml_errors(text: str, name: str = "fixture.yaml") -> list[str]:
    return check_naming.check_identifier_tokens_in_text(
        text, display_path=name, suffix=".yaml"
    )


def _md_errors(text: str, name: str = "fixture.md") -> list[str]:
    return check_naming.check_identifier_tokens_in_text(
        text, display_path=name, suffix=".md"
    )


def _sysml_errors(text: str, name: str = "fixture.sysml") -> list[str]:
    return check_naming.check_identifier_tokens_in_text(
        text, display_path=name, suffix=".sysml"
    )


# ---------------------------------------------------------------------------
# Quoted YAML values are governed (the scrubber hole this suite pins shut)
# ---------------------------------------------------------------------------


def test_quoted_yaml_bogus_prefix_is_rejected():
    """requirement_id: "BOGUS-AEBS-001" — quoted values MUST be inspected."""
    errors = _yaml_errors('requirement_id: "BOGUS-AEBS-001"\n')
    assert any("BOGUS" in e for e in errors), errors


def test_quoted_yaml_valid_id_is_accepted():
    assert _yaml_errors('requirement_id: "REQ-AEBS-001"\n') == []


def test_unquoted_yaml_bogus_prefix_is_rejected():
    errors = _yaml_errors("requirement_id: BOGUS-AEBS-001\n")
    assert any("BOGUS" in e for e in errors), errors


def test_invalid_subject_is_rejected():
    errors = _yaml_errors('id: REQ-UNKNOWN-001\n')
    assert any("'UNKNOWN'" in e for e in errors), errors


def test_valid_legacy_subject_mw_is_accepted():
    """MW is a registered subject namespace; E-MW-011 is a grandfathered
    legacy identity and stays valid (stable, provenance-bearing)."""
    assert _yaml_errors("evidence_id: E-MW-011\n") == []


def test_grandfathered_legacy_identities_are_closed_sets():
    """Retired grammars accept ONLY the enumerated identities."""
    for identity in sorted(check_naming._GRANDFATHERED_IDENTITIES):
        assert _yaml_errors(f"id: {identity}\n") == [], identity
    # Sibling spellings under the retired grammars are rejected
    # deterministically — grandfathering never licenses new IDs.
    for sibling in ("E-MW-999", "E-AEBS-001", "N-AEBS-015", "N-MW-010", "N-FOO-001"):
        errors = _yaml_errors(f"id: {sibling}\n")
        assert errors, f"{sibling} must be rejected"
        assert any("unregistered" in e for e in errors), (sibling, errors)


def test_new_canonical_need_and_evidence_forms_are_accepted():
    assert _yaml_errors("id: NEED-AEBS-001\n") == []
    assert _yaml_errors("id: EVID-MW-015\n") == []


def test_config_identity_form_is_accepted():
    assert _yaml_errors('configuration: "MW-CONFIG-001"\n') == []
    assert _yaml_errors('configuration: "AEBS-CONFIG-010-001"\n') == []


def test_tail_of_longer_id_is_not_matched():
    """AC-MW-010-02 must not surface a standalone MW-010-02 token."""
    assert _yaml_errors("criterion AC-MW-010-02 and baseline BL-MW-010-P12\n") == []


def test_tail_of_de4sdv_prefix_is_not_matched():
    """The all-caps grammar matches `DE4SDV-VSS-EXT` as ONE token (the old
    letter-start grammar could not) — and it is a registered free-form
    prefix, so it is accepted, never misread as a tail like `SDV-…`."""
    text = "source_id: DE4SDV-VSS-EXT"
    tokens = [m.group(0) for m in check_naming._ID_TOKEN.finditer(text)]
    assert tokens == ["DE4SDV-VSS-EXT"]
    assert _yaml_errors(text) == []


# ---------------------------------------------------------------------------
# Artifact-aware preparation (prose/examples outside enforcement)
# ---------------------------------------------------------------------------


def test_sysml_doc_comment_does_not_flag_prose_ids():
    """SysML doc/comment content is not a governed identifier surface."""
    text = (
        "doc /* candidate IDs like BOGUS-AEBS-001 are discussed in prose. */\n"
        "package DE4SDV_X {}\n"
    )
    assert _sysml_errors(text) == []


def test_sysml_quoted_charset_fragment_does_not_false_positive():
    text = 'attribute spec := "[A-Z0-9-]";\n'
    assert _sysml_errors(text) == []


def test_markdown_fenced_example_is_exempt():
    """Fenced code blocks are illustrative examples, not governed IDs."""
    text = "Example:\n\n```yaml\nrequirement_id: \"BOGUS-AEBS-001\"\n```\n"
    assert _md_errors(text) == []


def test_markdown_inline_identifier_is_governed():
    errors = _md_errors("Trace `REQ-UNKNOWN-001` to its need.\n")
    assert any("'UNKNOWN'" in e for e in errors), errors


def test_markdown_prose_technical_tokens_do_not_false_positive():
    text = (
        "Hash: SHA-256 and SHA-1 are algorithms.\n"
        "Range: A-Z charset. See #L743-L754.\n"
        "Prose: SERVER-IPv4 and AI-Ready stay out by grammar.\n"
    )
    assert _md_errors(text) == []


def test_external_project_names_do_not_false_positive():
    assert _md_errors("Use S-CORE and SAF-SysMLV2 and COVESA-VSS-VEHICLE-SPEED.\n") == []


# ---------------------------------------------------------------------------
# Whole-repository surface (observable behavior on the real tree)
# ---------------------------------------------------------------------------


def test_repository_governed_surface_passes():
    """The governed surface must be clean as committed (no known stales)."""
    assert check_naming.check_identifier_tokens() == []


def test_broadened_surface_actually_scans_ple_and_implementation():
    """Feature-model and implementation text files are inside the surface."""
    scanned = [str(p) for p in check_naming._iter_governed_text_files()]
    joined = "\n".join(scanned)
    assert (
        "model-based-product-line-engineering/feature-models/sdv_product_line.yaml"
        in joined
    )
    assert "implementation/aaos-sdv-reference-interop-bench/README.md" in joined
    assert "approach/framework/ontology/de4sdv-basic-ontology.yaml" in joined


def test_retained_evidence_and_adrs_are_excluded():
    scanned = [str(p) for p in check_naming._iter_governed_text_files()]
    joined = "\n".join(scanned)
    assert "implementation/aaos-sdv-reference-interop-bench/evidence/" not in joined
    assert "docs/architecture-decisions/" not in joined
    assert "docs/plans/2026-07-27-aebs-009c-009i.md" not in joined
    assert "compliance/safety/hazard-analysis-template.md" not in joined


def test_python_is_not_token_scanned():
    scanned = [str(p) for p in check_naming._iter_governed_text_files()]
    assert not any(p.endswith(".py") for p in scanned)


# ---------------------------------------------------------------------------
# Filename + diagram checks (regression guards)
# ---------------------------------------------------------------------------


def test_project_sysml_filenames_are_lower_snake_case():
    errors = check_naming.check_sysml_filenames()
    assert not errors, "\n".join(errors)


def test_no_canonical_concern_filename_embeds_increment_numbers():
    """The 010 visualization slices are migrated (M11/M12 executed)."""
    errors = check_naming.check_sysml_filenames()
    assert not any("aebs_010" in e for e in errors), errors


def test_no_stale_diagram_names():
    errors = check_naming.check_view_diagram_names()
    assert not errors, "\n".join(errors)


def test_registry_coverage_matches_convention_doc():
    """Every checker prefix and subject must appear in the conventions doc."""
    doc = (ROOT / "docs/naming/naming-conventions.md").read_text()
    for prefix in check_naming.STRICT_PREFIXES | check_naming.FREE_FORM_PREFIXES:
        assert f"`{prefix}`" in doc, f"prefix {prefix} missing from conventions doc"
    for subject in check_naming.REGISTERED_SUBJECTS:
        assert f"`{subject}`" in doc, f"subject {subject} missing from conventions doc"


def test_subject_registry_grammar_is_consistent():
    """R152 is a rest segment of SRC-UNECE-R152, not a subject."""
    assert "UNECE" in check_naming.REGISTERED_SUBJECTS
    assert "R152" not in check_naming.REGISTERED_SUBJECTS
    assert "R152" not in check_naming.STRICT_PREFIXES | check_naming.FREE_FORM_PREFIXES
    prepared = check_naming._prepare_text_for_suffix("SRC-UNECE-R152", suffix=".yaml")
    tokens = [m.group(0) for m in check_naming._ID_TOKEN.finditer(prepared)]
    assert "SRC-UNECE-R152" in tokens


def test_sha_names_are_documented_non_governed():
    assert "SHA-256" in check_naming._EXTERNAL_ID_NAMES
    assert "SHA-1" in check_naming._EXTERNAL_ID_NAMES