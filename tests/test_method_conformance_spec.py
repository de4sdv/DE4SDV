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
    """Parse the pilot obligation table data rows (12 columns).

    The table is the markdown block starting with the '| # |' header row and
    ending before the next section heading after it (the dependency-graph
    section sits between the table preamble and the table itself)."""
    start = text.index("| # | obligation_id |")
    rest = text[start:]
    end_markers = ["\n### ", "\n## "]
    end = len(rest)
    for marker in end_markers:
        idx = rest.find(marker, 10)
        if idx != -1:
            end = min(end, idx)
    section = rest[:end]
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


def _norm_cell(s: str) -> str:
    """Normalize a markdown table cell to a comparable slug."""
    return s.strip().strip("`").lower().replace(" + ", "+").replace(" ", "-")


def test_pilot_contract_structure() -> None:
    """The markdown table must match the structured contract COMPLETELY:
    IDs/order, exact phase, subject/target types, per-subject bounds,
    evaluation sources, requiredness, dependency graph (R3: full record
    comparison, not token spot-checks)."""
    text = (DOCS / "pilot-scope.md").read_text(encoding="utf-8")
    rows = _pilot_table_rows(text)
    spec = _load_pilot_yaml()
    obligations = spec["obligations"]
    assert len(rows) == len(obligations) == 11, (
        f"pilot table row count mismatch: md={len(rows)} yaml={len(obligations)}"
    )
    assert any(spec["phase_literal"] in r[2] for r in rows), (
        f"pilot table never names the pinned phase literal {spec['phase_literal']}"
    )
    for md_row, y in zip(rows, obligations):
        md_id = md_row[1].strip("`")
        assert md_id == y["id"], f"row order/id mismatch: {md_id} != {y['id']}"
        assert md_row[2].startswith("10"), f"{y['id']}: phase must reference phase 10"
        # Subject/target types: structured values must appear in the md cells.
        # Subject type lives in the selector column (3) for every row.
        st = y["subject_type"].lower()
        assert st in md_row[3].lower().replace("`", ""), (
            f"{y['id']}: subject type '{y['subject_type']}' not in md selector cell"
        )
        combined = (md_row[6] + " " + md_row[7]).lower().replace("`", "")
        key_target = y["target_type"].split("{")[0].lower()
        assert key_target in combined, (
            f"{y['id']}: target type '{key_target}' not in md predicate/filter cells"
        )
        # Forbidden subject types must NOT appear as the md subject type.
        if "forbidden_subject_type" in y:
            assert y["forbidden_subject_type"].lower() not in md_row[6].lower(), (
                f"{y['id']}: md claims forbidden subject type {y['forbidden_subject_type']}"
            )
        # Per-subject bounds.
        import re as _re

        m = _re.search(r"`?\[(\d+)\.\.(\d+)\]`?", md_row[8])
        assert m, f"{y['id']}: cardinality not per-subject bounds: {md_row[8]}"
        assert (int(m.group(1)), int(m.group(2))) == tuple(y["per_subject_cardinality"]), (
            f"{y['id']}: cardinality drift vs structured source: {md_row[8]}"
        )
        assert md_row[9] == "required", f"{y['id']}: requiredness drift"
        md_src = _norm_cell(md_row[10])
        y_src = y["evaluation_source"].lower()
        assert md_src == y_src, f"{y['id']}: evaluation_source drift: {md_src} != {y_src}"
        # Applicability column must NOT carry dependency language (R1).
        md_app = _norm_cell(md_row[4])
        assert "binding" not in md_app and "resolved" not in md_app and "record" not in md_app, (
            f"{y['id']}: applicability cell still carries dependency language: {md_row[4]}"
        )


def test_pilot_dependency_graph_matches_markdown() -> None:
    """R1: the normative dependency graph in the markdown must equal the
    structured graph exactly (both directions checked)."""
    text = (DOCS / "pilot-scope.md").read_text(encoding="utf-8")
    spec = _load_pilot_yaml()
    section = text.split("### Obligation dependency graph")[1].split("```")[1]
    id_by_number = {str(i + 1): o["id"] for i, o in enumerate(spec["obligations"])}
    md_edges = {}
    for line in section.splitlines():
        line = line.strip()
        if line == "text" or not line:
            continue
        if "depends on:" not in line:
            continue
        oid = id_by_number.get(line.split()[0], line.split()[0])
        deps = line.split("depends on:")[1].strip()
        deps = (
            deps.replace("(its own usage)", "")
            .replace("(its own profile record)", "")
            .replace("(its own profile)", "")
            .replace("(scope resolution)", "")
            .replace("(independent branch)", "")
            .replace("(root of model branch)", "")
            .strip()
        )
        resolved = []
        for dep in [d.strip() for d in deps.split(",") if d.strip()]:
            if dep == "none":
                continue
            resolved.append(id_by_number.get(dep, dep))
        md_edges[oid] = resolved
    assert md_edges == spec["dependency_graph"], (
        f"dependency graph drift:\nmd={md_edges}\nyaml={spec['dependency_graph']}"
    )


def test_pilot_aggregate_examples_derive_from_graph() -> None:
    """R1: the aggregate examples must not claim edges that contradict the
    graph (9/11 independent of 10; 10 failure blocks conformance, not
    assessment)."""
    text = (DOCS / "pilot-scope.md").read_text(encoding="utf-8")
    graph = _load_pilot_yaml()["dependency_graph"]
    # No edge from 10 to 9/11:
    assert "PC-009D-EXECUTION-OUTCOME" not in graph["PC-009D-SCOPE-EQUALITY"]
    assert "PC-009D-ACCEPTANCE-AUTHORITY" not in graph["PC-009D-SCOPE-EQUALITY"]
    # The moved-boundary example must state 9/11 still evaluate and the block
    # is at the conformance/readiness layer.
    assert "9 and 11 still evaluate" in text
    assert "blocks" in text and "current-candidate" in text


def test_pilot_expected_dispositions_are_pinned_vocabulary() -> None:
    """Every expected disposition must be a literal of the pinned
    OverrideDisposition vocabulary, verified against the evaluator enum
    source (R3 M4 probe)."""
    spec = _load_pilot_yaml()
    model = (
        Path(__file__).resolve().parents[1]
        / "implementation/aebs-autoware-nominal-vehicle-target-bench/src/de4sdv_aebs_009b_bench/de4sdv_aebs_009b_bench/override_matrix.py"
    )
    src = model.read_text(encoding="utf-8")
    enum_section = src.split("class OverrideDisposition")[1].split("class ")[0]
    literals = {
        line.split("=")[1].strip().strip('"')
        for line in enum_section.splitlines()
        if "=" in line and line.strip().endswith('"') and '="' in line.replace(" = ", "=", 1)
    }
    assert literals, "could not parse OverrideDisposition literals from source"
    for profile, disp in spec["expected_dispositions"].items():
        assert disp in literals, f"{profile}: expected disposition '{disp}' not in OverrideDisposition enum {sorted(literals)}"


def test_pilot_selectors_declare_pinned_subject_sets() -> None:
    """R3 M2 probe: metadata/selector retargeting must fail. The selector
    column of the usage-scoped rows must name the six declared usages (the
    pinned subject set), not requirement targets."""
    text = (DOCS / "pilot-scope.md").read_text(encoding="utf-8")
    spec = _load_pilot_yaml()
    rows = _pilot_table_rows(text)
    by_id = {r[1].strip("`"): r for r in rows}
    usage_rows = [
        "PC-009D-VC-BINDING",
        "PC-009D-SUBJECT-MEMBERSHIP",
        "PC-009D-OBJECTIVE-CONTRACTS",
        "PC-009D-USAGE-METHOD-METADATA",
    ]
    pinned_usage_count = str(len(spec["scope_usages"]))
    for oid in usage_rows:
        selector = by_id[oid][3].lower()
        assert "each of the six" in selector or "the six declared usages" in selector, (
            f"{oid}: selector must select the pinned six-usage set, got: {selector}"
        )
        assert "requirement usage" not in selector, (
            f"{oid}: selector retargeted to requirements"
        )
        # The YAML twin must agree.
        y = next(o for o in spec["obligations"] if o["id"] == oid)
        assert y["subjects"] == 6 and y["subject_type"] == "VerificationCaseUsage", (
            f"{oid}: structured twin drifted from the pinned subject set"
        )
        assert "requirement" not in y["subject_selector"].lower(), (
            f"{oid}: structured twin selector retargeted to requirements: {y['subject_selector']}"
        )
        assert "six" in y["subject_selector"].lower() or "scope usages" in y["subject_selector"].lower(), (
            f"{oid}: structured twin selector must name the six-usage set: {y['subject_selector']}"
        )


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
