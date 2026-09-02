"""Tests for scripts/check_naming.py — conservative naming/identity checks.

The registry contract lives in docs/naming/naming-conventions.md; these tests
pin the checker's behavior (registry enforcement, exemptions, batch-2
advisories) so the convention cannot silently regress.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import check_naming  # noqa: E402


# ---------------------------------------------------------------------------
# Filename shape
# ---------------------------------------------------------------------------


def test_project_sysml_filenames_are_lower_snake_case():
    errors, _ = check_naming.check_sysml_filenames()
    assert not errors, "\n".join(errors)


def test_batch2_pending_advisory_lists_scheduled_renames():
    """The seven INC-AEBS-010 visualization slices are documented batch-2 work."""
    pending = check_naming.batch2_pending_files()
    assert len(pending) == 7
    assert all("aebs_010_visualization_" in name for name in pending)


def test_batch2_advisory_disappears_after_migration():
    """Simulate a tree where the batch-2 renames have been applied."""
    original = set(check_naming._BATCH2_PENDING)
    try:
        check_naming._BATCH2_PENDING.clear()
        pending = check_naming.batch2_pending_files()
        assert pending == []
    finally:
        check_naming._BATCH2_PENDING.update(original)


# ---------------------------------------------------------------------------
# Identifier registry
# ---------------------------------------------------------------------------


def test_registered_inc_id_accepted():
    assert check_naming.check_identifier_tokens() == [] or all(
        "INC-" not in e for e in check_naming.check_identifier_tokens()
    )


def test_unregistered_prefix_rejected():
    import re

    text = "links REQ-AEBS-001 and BOGUS-AEBS-001 in one doc"
    tokens = [
        m
        for m in check_naming._ID_TOKEN.finditer(text)
    ]
    prefixes = {m.group(1) for m in tokens}
    assert "BOGUS" in prefixes
    assert "REQ" in prefixes
    # the full checker path rejects BOGUS via the same registry
    assert "BOGUS" not in check_naming.STRICT_PREFIXES | check_naming.FREE_FORM_PREFIXES


def test_tail_of_longer_id_is_not_matched():
    """AC-MW-010-02 must not surface a standalone MW-010-02 token."""
    text = "criterion AC-MW-010-02 and baseline BL-MW-010-P12"
    tokens = [m.group(0) for m in check_naming._ID_TOKEN.finditer(text)]
    assert tokens == ["AC-MW-010-02", "BL-MW-010-P12"]


def test_tail_of_de4sdv_prefix_is_not_matched():
    """DE4SDV-… contains a digit, so the prefix regex cannot match it at all —
    neither as `DE4SDV-…` nor as a tail like `SDV-…` (the old lookbehind bug).
    DE4SDV-* artifact references are therefore outside ID-token validation by
    construction and documented as a free-form prefix in the registry."""
    text = "source_id: DE4SDV-VSS-EXT"
    tokens = [m.group(0) for m in check_naming._ID_TOKEN.finditer(text)]
    assert tokens == []


def test_config_identity_form_is_documented_shape():
    """<SUBJECT>-CONFIG-<SEQ> identities parse and are registry-documented."""
    assert check_naming._CONFIG_IDENTITY.fullmatch("MW-CONFIG-001")
    assert check_naming._CONFIG_IDENTITY.fullmatch("AEBS-CONFIG-010-001")
    assert not check_naming._CONFIG_IDENTITY.fullmatch("MW-CONFIG-XX")


def test_external_id_names_exempt():
    """S-CORE and friends are upstream names, not DE4SDV registry IDs."""
    assert "S-CORE" in check_naming._EXTERNAL_ID_NAMES
    assert "COVESA-VSS-VEHICLE-SPEED" in check_naming._EXTERNAL_ID_NAMES


# ---------------------------------------------------------------------------
# Generated diagram consistency
# ---------------------------------------------------------------------------


def test_no_stale_diagram_names():
    errors = check_naming.check_view_diagram_names()
    assert not errors, "\n".join(errors)


def test_registry_coverage_matches_convention_doc():
    """Every checker prefix must appear in the conventions doc registry."""
    doc = (ROOT / "docs/naming/naming-conventions.md").read_text()
    for prefix in check_naming.STRICT_PREFIXES | check_naming.FREE_FORM_PREFIXES:
        assert f"`{prefix}`" in doc, f"prefix {prefix} missing from conventions doc"
    for subject in check_naming.REGISTERED_SUBJECTS:
        assert subject in doc, f"subject {subject} missing from conventions doc"
