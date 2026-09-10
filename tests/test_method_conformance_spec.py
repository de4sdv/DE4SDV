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


def _declared_reason_code_list(text: str) -> list[str]:
    """Same as _declared_reason_codes but preserving duplicates and order."""
    head = text.split("PERMITTED_EMPTY sub-vocabulary")[0]
    codes = re.findall(r"^([A-Z][A-Z_]{2,})\s{2,}", head, re.M)
    return [c for c in codes if c not in _NON_REASON_UPPER]


def test_reason_vocabulary_has_no_duplicate_declarations() -> None:
    """A code declared twice in the vocabulary block is an ambiguity defect
    and must fail (R4 follow-up: set conversion must not erase duplicates)."""
    codes = _declared_reason_code_list(
        (DOCS / "result-algebra.md").read_text(encoding="utf-8")
    )
    dupes = sorted({c for c in codes if codes.count(c) > 1})
    assert not dupes, f"duplicate reason declarations: {dupes}"


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


def _compat_table_rows(text: str) -> list[list[str]]:
    """Parse the State/reason compatibility table data rows."""
    section = text.split("## State/reason compatibility table")[1].split("## ")[0]
    rows = []
    for line in section.splitlines():
        s = line.strip()
        if s.startswith("|") and not s.startswith("|--") and "---" not in s:
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) == 5 and cells[0] != "assessment_coverage":
                rows.append(cells)
    return rows


def _pilot_table_rows(text: str) -> list[list[str]]:
    """Parse the pilot obligation table data rows (12 columns)."""
    section = text.split("## Bounded pilot obligation table")[1].split("###")[0]
    rows = []
    for line in section.splitlines():
        s = line.strip()
        if s.startswith("|") and "---" not in s:
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) == 12 and cells[0] not in {"#", "# (obligation_id)"}:
                rows.append(cells)
    return rows


def test_state_reason_compatibility_table_structure() -> None:
    """The compatibility table must contain its six legal-state rows with
    exact state tuples — headings alone do not pass (R4)."""
    text = (DOCS / "result-algebra.md").read_text(encoding="utf-8")
    rows = _compat_table_rows(text)
    states = [(r[0], r[1], r[2]) for r in rows]
    expected = [
        ("ASSESSED", "COMPLETE", "PASS"),
        ("ASSESSED", "COMPLETE", "FAIL"),
        ("ASSESSED", "COMPLETE", "NOT_APPLICABLE"),
        ("ASSESSED", "INDETERMINATE", "null"),
        ("ASSESSED", "ERROR", "null"),
        ("UNASSESSED", "null", "null"),
    ]
    assert states == expected, f"compatibility table state tuples drifted: {states}"
    # Each FAIL/INDETERMINATE/ERROR/UNASSESSED row must name required content.
    for r in rows:
        if r[2] in {"FAIL", "NOT_APPLICABLE"} or r[1] in {"INDETERMINATE", "ERROR"} or r[0] == "UNASSESSED":
            assert "at least one" in r[3] or "exactly one" in r[3] or r[3] == "`[]`", (
                f"row {r[0]}/{r[1]}/{r[2]} lacks required-reason content: {r[3]}"
            )


def _load_pilot_yaml() -> dict:
    import yaml

    return yaml.safe_load((DOCS / "pilot-obligations.yaml").read_text(encoding="utf-8"))


def test_pilot_contract_structure() -> None:
    """The pilot obligation table must match its structured source of truth
    row-for-row with required fields (R4): IDs, subject types, target types,
    per-subject bounds, evaluation sources."""
    text = (DOCS / "pilot-scope.md").read_text(encoding="utf-8")
    rows = _pilot_table_rows(text)
    spec = _load_pilot_yaml()
    obligations = spec["obligations"]
    assert len(rows) == len(obligations) == 11, (
        f"pilot table row count mismatch: md={len(rows)} yaml={len(obligations)}"
    )
    # The exact pinned phase literal must appear in the table's phase column
    # (first data row pins it for the whole table; every row references phase 10).
    assert any(spec["phase_literal"] in r[2] for r in rows), (
        f"pilot table never names the pinned phase literal {spec['phase_literal']}"
    )
    for md_row, y in zip(rows, obligations):
        # md columns: #, obligation_id, phase, subject_selector, applicability,
        # population_policy, predicate, target_filters, cardinality, required,
        # evaluation_source, expected disposition
        md_id = md_row[1].strip("`")
        assert md_id == y["id"], f"row order/id mismatch: {md_id} != {y['id']}"
        assert md_row[2].startswith("10"), f"{y['id']}: phase literal must reference phase 10 (pinned {spec['phase_literal']})"
        pred_tokens = [t.lower() for t in y["predicate"].replace("-", " ").split() if len(t) > 3]
        md_pred = md_row[6].lower().replace("`", "")
        missing_tokens = [t for t in pred_tokens if t not in md_pred]
        assert not missing_tokens, (
            f"{y['id']}: predicate family mismatch; missing tokens {missing_tokens} in: {md_row[6][:80]}"
        )
        import re as _re

        m = _re.search(r"`?\[(\d+)\.\.(\d+)\]`?", md_row[8])
        assert m, f"{y['id']}: cardinality not per-subject bounds: {md_row[8]}"
        lo, hi = m.group(1), m.group(2)
        assert (int(lo), int(hi)) == tuple(y["per_subject_cardinality"]), (
            f"{y['id']}: cardinality drift vs structured source: {bounds}"
        )
        assert md_row[9] == "required", f"{y['id']}: requiredness drift"
        md_src = md_row[10].strip("`").lower().replace(" + ", "+").replace(" ", "-")
        y_src = y["evaluation_source"].lower()
        assert md_src == y_src, (
            f"{y['id']}: evaluation_source drift: {md_src} != {y_src}"
        )
        assert y["subject_type"] and y["target_type"], f"{y['id']}: missing type declarations"


def test_pilot_population_is_per_subject() -> None:
    """R2c regression guard: execution/acceptance obligations count targets per
    profile subject ([1..1] each), never a global [6..6] count over six
    per-profile subjects."""
    spec = _load_pilot_yaml()
    by_id = {o["id"]: o for o in spec["obligations"]}
    for oid in ("PC-009D-EXECUTION-RECORD", "PC-009D-EXECUTION-OUTCOME", "PC-009D-SCOPE-EQUALITY", "PC-009D-ACCEPTANCE-AUTHORITY"):
        o = by_id[oid]
        assert o["subjects"] == 6 and o["per_subject_cardinality"] == [1, 1], (
            f"{oid} must be 6 profile subjects with [1..1] per-subject cardinality"
        )


def test_pilot_phase_literal_is_exact() -> None:
    """R2a regression guard: the pinned phase literal must be the real
    MethodPhase literal (phase10_vvEvidence), not an invented name."""
    spec = _load_pilot_yaml()
    assert spec["phase_literal"] == "phase10_vvEvidence"
    model = Path(__file__).resolve().parents[1] / (
        "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml"
    )
    assert f"{spec['phase_literal']} {{" in model.read_text(encoding="utf-8"), (
        "pinned phase literal does not exist in the method kernel"
    )


def test_pilot_expected_outcomes_cover_review_examples() -> None:
    """The maintained contract must declare expected dispositions for the
    re-review examples: missing case, missing profile, failed execution,
    incomplete scope, absent attestation."""
    text = (DOCS / "pilot-scope.md").read_text(encoding="utf-8")
    for needle, context in (
        ("REQUIRED_RELATION_MISSING", "missing case/profile"),
        ("INPUT_UNAVAILABLE", "incomplete scope"),
        ("EXECUTION_FAILED", "failed execution"),
        ("EVIDENCE_SCOPE_MISMATCH", "moved tested boundary"),
        ("ACCEPTANCE_AUTHORITY_MISSING", "absent attestation"),
        ("NOT_ATTEMPTED", "prerequisite-blocked children"),
    ):
        assert needle in text, f"pilot scope missing expected outcome {needle} ({context})"


def test_pilot_declares_expected_aggregate_outcomes() -> None:
    """Historical-realization and moved-boundary aggregate outcomes must be
    declared (per-obligation and aggregate), not left for B to invent."""
    text = (DOCS / "pilot-scope.md").read_text(encoding="utf-8")
    assert "Expected aggregate outcomes" in text
    assert "ASSESSED" in text and "COMPLETE" in text and "FAIL" in text
    assert "UNASSESSED" in text, "moved-boundary aggregate outcome missing"


def test_pilot_scope_names_acceptance_authority_gap() -> None:
    text = (DOCS / "pilot-scope.md").read_text(encoding="utf-8")
    assert "ConsciousOverrideVerification" in text
    assert "AEBSAutowareLinuxLidarCamera" in text
    assert "ACCEPTANCE_AUTHORITY_MISSING" in text
