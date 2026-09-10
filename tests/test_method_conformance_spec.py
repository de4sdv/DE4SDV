"""Freeze-integrity tests for the method-conformance specification.

The frozen planning baseline is the conformance specification. Its committed
copy must remain byte-identical (digest 427410f3...), and the extracted MC
matrix must match a fresh extraction. Drift in either is a specification
amendment that must go through a reviewed ADR change, not an edit.
"""

import hashlib
import json
import re
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs" / "method-conformance"
FROZEN_DIGEST = "427410f3070ed591287ec0dd3b819be7e95ee22fa7608b4c87d1e82192abd661"


def _baseline_text() -> str:
    return (DOCS / "conformance-baseline.md").read_text(encoding="utf-8")


def test_frozen_baseline_digest_unchanged() -> None:
    digest = hashlib.sha256(_baseline_text().encode("utf-8")).hexdigest()
    assert digest == FROZEN_DIGEST, (
        "conformance-baseline.md drifted from the frozen specification digest; "
        "changes require a reviewed amendment (ADR 0019)"
    )


def test_mc_matrix_matches_baseline_extraction() -> None:
    rows = []
    for line in _baseline_text().splitlines():
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
    matrix = json.loads((DOCS / "mc-matrix.json").read_text(encoding="utf-8"))
    assert matrix["count"] == 40, "MC case count changed"
    assert matrix["cases"] == rows, "mc-matrix.json does not match the committed baseline"


def test_mc_owners_are_within_b_c_d() -> None:
    matrix = json.loads((DOCS / "mc-matrix.json").read_text(encoding="utf-8"))
    assert {case["owner"] for case in matrix["cases"]} == {"B", "C", "D"}


def test_result_algebra_vocabulary_is_finite_and_pinned() -> None:
    text = (DOCS / "result-algebra.md").read_text(encoding="utf-8")
    required = [
        "CONTRACT_UNAVAILABLE",
        "OUTSIDE_REQUESTED_SCOPE",
        "NOT_ATTEMPTED",
        "APPLICABILITY_UNRESOLVED",
        "INPUT_UNAVAILABLE",
        "INVALID_CONTRACT",
        "BINDING_MISMATCH",
        "SCOPE_RESOLUTION_ERROR",
        "ACCEPTANCE_AUTHORITY_MISSING",
        "STALE_INPUT",
    ]
    for code in required:
        assert code in text, f"reason vocabulary lost {code}"


def test_pilot_scope_names_acceptance_authority_gap() -> None:
    text = (DOCS / "pilot-scope.md").read_text(encoding="utf-8")
    assert "ConsciousOverrideVerification" in text
    assert "AEBSAutowareLinuxLidarCamera" in text
    assert "ACCEPTANCE_AUTHORITY_MISSING" in text
