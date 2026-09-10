"""Freeze-integrity tests for the method-conformance specification.

The frozen planning baseline is the conformance specification. Its committed
copy must remain byte-identical (digest 427410f3...), the extracted MC matrix
must match a fresh extraction, and the reason vocabulary must match the exact
declared set - additions and removals both fail. Drift in any of these is a
specification amendment that must go through a reviewed ADR change, not an edit.
"""

import hashlib
import json
import re
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs" / "method-conformance"
FROZEN_DIGEST = "427410f3070ed591287ec0dd3b819be7e95ee22fa7608b4c87d1e82192abd661"

# Exact finite reason vocabulary declared by result-algebra.md (normative set).
REASON_VOCABULARY = {
    "CONTRACT_UNAVAILABLE",
    "OUTSIDE_REQUESTED_SCOPE",
    "NOT_ATTEMPTED",
    "APPLICABILITY_UNRESOLVED",
    "INPUT_UNAVAILABLE",
    "INVALID_CONTRACT",
    "BINDING_MISMATCH",
    "SCOPE_RESOLUTION_ERROR",
    "POPULATION_POLICY_VIOLATION",
    "EVIDENCE_SCOPE_MISMATCH",
    "ACCEPTANCE_AUTHORITY_MISSING",
    "STALE_INPUT",
    "REQUIRED_RELATION_MISSING",
    "EXECUTION_FAILED",
    "EVALUATOR_FAILURE",
    "NOT_APPLICABLE_REASON",
}
PERMITTED_EMPTY_VOCABULARY = {"NO_ELIGIBLE_SUBJECTS", "EXPLICIT_DISPOSITION"}


def _baseline_text() -> str:
    return (DOCS / "conformance-baseline.md").read_text(encoding="utf-8")


def test_frozen_baseline_digest_unchanged() -> None:
    # Raw bytes, not decoded text: an encoding/line-ending mutation must fail.
    raw = (DOCS / "conformance-baseline.md").read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == FROZEN_DIGEST, (
        "conformance-baseline.md drifted from the frozen specification digest; "
        "changes require a reviewed amendment (ADR 0019)"
    )


def _extract_mc_rows(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("| MC-"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) == 4 and cells[0] != "ID":
                rows.append(
                    {
                        "id": cells[0],
                        "scenario": cells[1],
                        "outcome": cells[2],
                        "owner": cells[3],
                    }
                )
    return rows


def test_mc_matrix_matches_baseline_extraction() -> None:
    rows = _extract_mc_rows(_baseline_text())
    matrix = json.loads((DOCS / "mc-matrix.json").read_text(encoding="utf-8"))
    assert matrix["count"] == 40, "MC case count changed"
    assert matrix["cases"] == rows, "mc-matrix.json does not match the committed baseline"


def test_mc_owners_are_within_b_c_d() -> None:
    matrix = json.loads((DOCS / "mc-matrix.json").read_text(encoding="utf-8"))
    assert {case["owner"] for case in matrix["cases"]} == {"B", "C", "D"}


# UPPER tokens that appear in the docs but are statuses/fields/abbreviations,
# not reason codes.
_NON_REASON_UPPER = {
    "ASSESSED", "UNASSESSED", "COMPLETE", "INDETERMINATE", "ERROR",
    "READY", "BLOCKED", "NOT_APPLICABLE", "TASK_ENTRY", "PHASE_EXIT",
    "PR_MERGE", "SHA", "JSON", "API", "MC", "ADR", "INC", "V1", "PASS", "FAIL",
    "TODO",
}


def _declared_reason_codes(text: str) -> set[str]:
    """Upper-snake tokens in definition position in the main vocabulary block.

    The PERMITTED_EMPTY sub-vocabulary block is excluded (checked separately).
    """
    head = text.split("PERMITTED_EMPTY sub-vocabulary")[0]
    codes = set(re.findall(r"^([A-Z][A-Z_]{2,})\s{2,}", head, re.M))
    return codes - _NON_REASON_UPPER


def _declared_sub_vocabulary(text: str) -> set[str]:
    section = text.split("```text\nNO_ELIGIBLE_SUBJECTS")[1].split("```")[0]
    return set(re.findall(r"^([A-Z][A-Z_]{2,})\s{2,}", "NO_ELIGIBLE_SUBJECTS" + section, re.M)) - _NON_REASON_UPPER


def test_reason_vocabulary_is_exact() -> None:
    """The doc's declared vocabulary must equal the pinned set exactly.

    Negative probes are intentional: removing a declared code or adding an
    unreviewed one must fail this test.
    """
    text = (DOCS / "result-algebra.md").read_text(encoding="utf-8")
    declared = _declared_reason_codes(text)
    assert declared == REASON_VOCABULARY, (
        f"reason vocabulary drift: missing={sorted(REASON_VOCABULARY - declared)}, "
        f"unexpected={sorted(declared - REASON_VOCABULARY)}"
    )
    sub = _declared_sub_vocabulary(text)
    assert sub == PERMITTED_EMPTY_VOCABULARY, (
        f"PERMITTED_EMPTY vocabulary drift: {sorted(sub ^ PERMITTED_EMPTY_VOCABULARY)}"
    )


def test_state_reason_compatibility_table_present() -> None:
    text = (DOCS / "result-algebra.md").read_text(encoding="utf-8")
    for required in (
        "State/reason compatibility table",
        "FAIL vs INDETERMINATE for the acceptance obligation",
        "PERMITTED_EMPTY sub-vocabulary",
    ):
        assert required in text, f"result-algebra.md lost required section: {required}"


def test_pilot_contract_is_instantiated() -> None:
    """The pilot obligations must be specified, not just named."""
    text = (DOCS / "pilot-scope.md").read_text(encoding="utf-8")
    for obligation in (
        "PC-009D-VC-EXISTS",
        "PC-009D-SUBJECT-MEMBERSHIP",
        "PC-009D-OBJECTIVE-CONTRACTS",
        "PC-009D-METHOD-METADATA",
        "PC-009D-EXECUTION-RECORDS",
        "PC-009D-ACCEPTANCE-AUTHORITY",
    ):
        assert obligation in text, f"pilot obligation missing: {obligation}"
    assert "rebinding rule" in text, "pilot scope lost the rebinding rule"


def test_pilot_scope_names_acceptance_authority_gap() -> None:
    text = (DOCS / "pilot-scope.md").read_text(encoding="utf-8")
    assert "ConsciousOverrideVerification" in text
    assert "AEBSAutowareLinuxLidarCamera" in text
    assert "ACCEPTANCE_AUTHORITY_MISSING" in text
