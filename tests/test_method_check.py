"""The pull-request method check: every declared increment, evaluated offline.

``scripts/method_check.py`` discovers the increments of an export (through
charters and short names), runs the evaluation entry point
``scripts/evaluate_increment.py`` once per increment, and writes one JSON
result plus a readable summary. Gaps never fail it; technical errors do.

Synthetic increments over the method layer of the frozen genuine-export cut;
no network. A transport spy stands in for the entry-point process where a test
only checks orchestration; one test runs the real entry point.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from de4sdv.semantic.remedies import SUBJECT_FIRST
from increment_model_fixtures import (
    ModelBuilder,
    increment_scenario,
    cut_method_builder,
    cut_workflow,
    kernel_qualified_name,
    set_check,
)
from scripts import method_check

ROOT = Path(__file__).resolve().parents[1]
GIT = "e" * 40
FIRST, SECOND, THIRD, FOURTH = "INC-FIXTURE-001", "INC-FIXTURE-002", "INC-FIXTURE-003", "INC-FIXTURE-004"
FIFTH = "INC-FIXTURE-005"
P0, P1, P2, P4, P5, P10 = ("phase0_incrementFraming", "phase1_concernFraming", "phase2_operationalContext",
                          "phase4_needs", "phase5_requirements", "phase10_vvEvidence")


def _gappy(builder: ModelBuilder) -> None:
    """First: the cut's workflow, one need without a stakeholder (one blocking gap)."""
    first = increment_scenario(builder, increment_id=FIRST, name="First")
    cut_workflow(first)
    need = first.needs[1]
    builder.remove(*[e for e in builder.elements if e.get("@type") == "StakeholderMembership"
                     and e.get("owningRelatedElement", {}).get("@id") == need["@id"]])


def _without_workflow(builder: ModelBuilder) -> None:
    """Second: a charter that declares no workflow (the method is unavailable)."""
    increment_scenario(builder, increment_id=SECOND, name="Second")


def _invalid_workflow(builder: ModelBuilder) -> None:
    """Third: the cut's workflow with an unknown check id (the method is invalid).

    The workflow is the builder's one cut workflow, so this goes in an export of its own.
    """
    third = increment_scenario(builder, increment_id=THIRD, name="Third")
    set_check(third, cut_workflow(third), "incrementHasAssumption", check="noSuchCheck")


def _overpopulated(builder: ModelBuilder) -> None:
    """Fourth: two engineering questions where the workflow allows exactly one (a population finding)."""
    fourth = increment_scenario(builder, increment_id=FOURTH, name="Fourth")
    cut_workflow(fourth)
    builder.usage("PartUsage", "fourthSecondQuestion", fourth.framing,
                  [builder.kernel_definition("IncrementEngineeringQuestion")])


def _declares_unchecked_phases(builder: ModelBuilder) -> None:
    """Fifth: complete, and its charter also declares phases 1 and 2, whose steps carry no checks in the cut."""
    fifth = increment_scenario(builder, increment_id=FIFTH, name="Fifth",
                               applicable_phases=(P0, P1, P2, P4, P5, P10))
    cut_workflow(fifth)


def _legacy_increment(builder: ModelBuilder) -> None:
    """After _gappy: a charter whose increment usage carries no identifier, like a legacy increment."""
    framing = next(e for e in builder.elements if e.get("declaredName") == "DE4SDV_FirstFraming")
    definition = next(e for e in builder.elements if e.get("declaredName") == "FirstIncrement")
    legacy = builder.usage("PartUsage", "incLegacy", framing, [definition])
    charter = builder.usage("PartUsage", "legacyCharter", framing,
                            [builder.kernel_definition("IncrementTraceObligations")])
    builder.attribute(charter, "increment", legacy, kind="PartUsage")


def _export(tmp_path: Path, *parts, git_commit: str = GIT, kernel: str = "cut") -> Path:
    builder = cut_method_builder("method-check") if kernel == "cut" else ModelBuilder(label="method-check")
    for part in parts:
        part(builder)
    path = tmp_path / "model-export.json"
    path.write_text(json.dumps(builder.export(git_commit=git_commit)))
    return path


@pytest.fixture(scope="module")
def real_reports(tmp_path_factory) -> dict[str, dict]:
    """One real entry-point report per outcome, evaluated in process once."""
    import importlib.util

    exports = {
        "valid": _export(tmp_path_factory.mktemp("valid"), _gappy, _without_workflow, _overpopulated),
        "invalid": _export(tmp_path_factory.mktemp("invalid"), _invalid_workflow),
    }
    spec = importlib.util.spec_from_file_location("evaluate_increment", ROOT / "scripts/evaluate_increment.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    reports = {}
    for increment, export in ((FIRST, "valid"), (SECOND, "valid"), (FOURTH, "valid"), (THIRD, "invalid")):
        code, report, _output = module.run(["--export", str(exports[export]), "--increment", increment])
        assert code == 0, report
        reports[increment] = report
    return reports


class EntryPointSpy:
    """Stands in for the entry-point process: records argv, writes a canned report."""

    def __init__(self, reports: dict[str, dict], codes: dict[str, int] | None = None,
                 stderr: str = "", silent: frozenset[str] = frozenset()) -> None:
        self.reports = reports
        self.codes = codes or {}
        self.stderr = stderr
        self.silent = silent  # increments for which the process writes no report
        self.calls: list[list[str]] = []

    def __call__(self, argv):
        argv = list(argv)
        self.calls.append(argv)
        increment = argv[argv.index("--increment") + 1]
        output = Path(argv[argv.index("--output") + 1])
        code = self.codes.get(increment, 0)
        if code in (0, 2) and increment not in self.silent:
            report = (self.reports[increment] if code == 0
                      else {"status": "refused", "reason": f"{increment} refused by the spy"})
            output.write_text(json.dumps(report))
        return method_check.RunnerResult(code, "", self.stderr)


def _run(tmp_path: Path, export: Path, runner, *, revision: str = GIT, extra=()):
    out = tmp_path / "result"
    summary = tmp_path / "summary.md"
    code = method_check.main(["--export", str(export), "--revision", revision, "--output-dir", str(out),
                              "--summary", str(summary), *extra], runner=runner)
    result = json.loads((out / "method-check.json").read_text()) if (out / "method-check.json").exists() else None
    return code, result, summary.read_text() if summary.exists() else ""


# -- orchestration (transport spy) -------------------------------------------


def test_each_declared_increment_runs_the_entry_point_once(tmp_path: Path, real_reports) -> None:
    export = _export(tmp_path, _gappy, _without_workflow)
    spy = EntryPointSpy(real_reports)
    code, result, _summary = _run(tmp_path, export, spy)
    assert code == 0
    assert [call[call.index("--increment") + 1] for call in spy.calls] == [FIRST, SECOND]
    for call in spy.calls:
        assert call[:2] == [sys.executable, str(ROOT / "scripts/evaluate_increment.py")]
        assert call[call.index("--export") + 1] == str(export)
        assert call[call.index("--query") + 1] == "all"
        assert "--binding" not in call
    assert [entry["id"] for entry in result["increments"]] == [FIRST, SECOND]
    assert result["revision"] == GIT
    assert result["errors"] == []


def test_gaps_never_fail_the_check(tmp_path: Path, real_reports) -> None:
    export = _export(tmp_path, _gappy)
    code, result, _summary = _run(tmp_path, export, EntryPointSpy(real_reports))
    assert code == 0
    entry = result["increments"][0]
    assert entry["outcome"] == "evaluated"
    assert entry["counts"]["blocking"] == 1
    assert entry["counts"]["blocking_by_kind"] == {"violation": 1}
    assert entry["counts"]["advisory"] == 4
    assert entry["next"]["gate"] == "needHasStakeholder"
    assert entry["next"]["stage"] == "phase4_needs"
    assert entry["phase_exits"]["phase4_needs"] == "BLOCKED"
    assert entry["phase_checks"]["phase0_incrementFraming"] == {"pass": 15, "total": 15, "not_applicable": 0}
    assert entry["phase_checks"]["phase4_needs"] == {"pass": 4, "total": 6, "not_applicable": 0}
    assert entry["evaluation"]["gaps"]["blocking"][0]["gate"] == "needHasStakeholder"


def test_an_unavailable_method_is_reported_not_failed(tmp_path: Path, real_reports) -> None:
    export = _export(tmp_path, _without_workflow)
    code, result, summary = _run(tmp_path, export, EntryPointSpy(real_reports))
    assert code == 0
    entry = result["increments"][0]
    assert entry["outcome"] == "method-unavailable"
    assert entry["next"] is None
    assert "the charter declares no workflow feature" in entry["diagnostics"][0]
    assert "the charter declares no workflow feature" in summary


def test_an_invalid_method_is_a_technical_error(tmp_path: Path, real_reports) -> None:
    export = _export(tmp_path, _gappy, _invalid_workflow)
    code, result, summary = _run(tmp_path, export, EntryPointSpy(real_reports))
    assert code == 1
    outcomes = {entry["id"]: entry["outcome"] for entry in result["increments"]}
    assert outcomes == {FIRST: "evaluated", THIRD: "method-invalid"}
    assert any(THIRD in error and "noSuchCheck" in error for error in result["errors"])
    assert "noSuchCheck" in summary


@pytest.mark.parametrize("code, outcome, expected, line", [
    (2, "refused", "refused by the spy",
     "**Refused by the evaluation entry point (exit code 2, technical error):** INC-FIXTURE-002 refused by the spy"),
    (1, "error", "Traceback: boom", "**Evaluation failed (exit code 1, technical error):** Traceback: boom"),
])
def test_a_refused_or_crashed_evaluation_is_a_technical_error(tmp_path: Path, real_reports, code, outcome,
                                                              expected, line):
    export = _export(tmp_path, _gappy, _without_workflow)
    spy = EntryPointSpy(real_reports, codes={SECOND: code}, stderr="Traceback: boom")
    exit_code, result, summary = _run(tmp_path, export, spy)
    assert exit_code == 1  # never a pass
    assert len(spy.calls) == 2  # one failure never skips the other increments
    outcomes = {entry["id"]: entry["outcome"] for entry in result["increments"]}
    assert outcomes == {FIRST: "evaluated", SECOND: outcome}
    assert any(SECOND in error and expected in error for error in result["errors"])
    assert line in summary.splitlines()
    assert f"| `{SECOND}` | {outcome} | none | - | - |" in summary.splitlines()


def test_a_stale_report_is_never_read_after_a_failed_evaluation(tmp_path: Path, real_reports) -> None:
    export = _export(tmp_path, _gappy)
    out = tmp_path / "result"
    out.mkdir()
    (out / f"{FIRST}.json").write_text(json.dumps(real_reports[FIRST]))  # left by an earlier run
    code, result, _summary = _run(tmp_path, export, EntryPointSpy(real_reports, silent=frozenset({FIRST})))
    assert code == 1
    assert result["increments"][0]["outcome"] == "error"
    assert "no report was written" in result["errors"][0]


def test_a_gate_error_under_a_readable_method_is_reported_not_failed(tmp_path: Path, real_reports) -> None:
    # An executable method whose aggregate state is ERROR (for example a gate
    # whose scope cannot be resolved) is model feedback, not an unreadable method.
    report = json.loads(json.dumps(real_reports[FIRST]))
    report["status"]["evaluation_state"] = "ERROR"
    export = _export(tmp_path, _gappy)
    code, result, _summary = _run(tmp_path, export, EntryPointSpy({FIRST: report}))
    assert code == 0
    assert result["increments"][0]["outcome"] == "evaluated"


def test_an_export_of_another_revision_is_refused(tmp_path: Path, real_reports) -> None:
    export = _export(tmp_path, _gappy, git_commit="f" * 40)
    spy = EntryPointSpy(real_reports)
    code, result, summary = _run(tmp_path, export, spy)
    assert code == 1
    assert spy.calls == []
    assert result["increments"] == []
    assert any("f" * 40 in error and GIT in error for error in result["errors"])
    assert "Technical error" in summary


def test_an_unreadable_export_is_a_technical_error(tmp_path: Path, real_reports) -> None:
    export = tmp_path / "model-export.json"
    export.write_text("{not json")
    spy = EntryPointSpy(real_reports)
    code, result, _summary = _run(tmp_path, export, spy)
    assert code == 1
    assert spy.calls == []
    assert result["errors"]


def test_an_export_whose_kernel_identity_fails_validation_is_refused(tmp_path: Path, real_reports) -> None:
    # The entry point refuses such an export with exit code 2; the check
    # refuses it once, before any increment, as a technical error.
    export = _export(tmp_path, _without_workflow, kernel="synthetic")
    spy = EntryPointSpy(real_reports)
    code, result, summary = _run(tmp_path, export, spy)
    assert code == 1
    assert spy.calls == []
    assert result["errors"][0].startswith("the export is refused: kernel binding validation failed closed")
    assert "- the export is refused: kernel binding validation failed closed" in summary


def test_the_revision_must_be_a_full_commit_id(tmp_path: Path, real_reports) -> None:
    export = _export(tmp_path, _gappy)
    with pytest.raises(SystemExit):
        method_check.main(["--export", str(export), "--revision", "HEAD", "--output-dir", str(tmp_path / "o")],
                          runner=EntryPointSpy(real_reports))


# -- a failed licensed export ----------------------------------------------------

EXPORT_DIAGNOSTIC = (
    "textual-notation-of-model/packages/features/area/area_framing.sysml:122:5: error "
    "(requirement-usage-subject-parameter-position): Subject must be the first input parameter"
)


def _report_export_failure(tmp_path: Path, diagnostics: Path):
    out = tmp_path / "result"
    summary = tmp_path / "summary.md"
    spy = EntryPointSpy({})
    code = method_check.main(["--export-failed", str(diagnostics), "--revision", GIT, "--output-dir", str(out),
                              "--summary", str(summary), "--artifact", f"method-check-{GIT}"], runner=spy)
    result = json.loads((out / "method-check.json").read_text())
    assert spy.calls == []  # nothing is evaluated
    assert (out / "method-check.md").read_text() == summary.read_text()
    return code, result, summary.read_text()


def test_a_failed_export_is_reported_with_its_diagnostics(tmp_path: Path) -> None:
    diagnostics = tmp_path / "export-diagnostics.txt"
    diagnostics.write_text(f"Syside rejected the reviewed baseline:\n{EXPORT_DIAGNOSTIC}\n")
    code, result, summary = _report_export_failure(tmp_path, diagnostics)
    assert code == 1  # a technical error, never a pass
    assert result["revision"] == GIT and result["increments"] == []
    assert result["errors"] == [method_check.EXPORT_FAILED]
    assert result["export_diagnostics"] == ["Syside rejected the reviewed baseline:", EXPORT_DIAGNOSTIC]
    assert f"- {method_check.EXPORT_FAILED}" in summary
    assert f"```text\nSyside rejected the reviewed baseline:\n{EXPORT_DIAGNOSTIC}\n```" in summary
    assert "The model declares no increment" not in summary
    assert "0 increments" not in summary
    assert f"artifact `method-check-{GIT}`" in summary


def test_a_failed_export_without_diagnostics_still_leaves_a_report(tmp_path: Path) -> None:
    # The export job can fail before the export runs (setup, network).
    code, result, summary = _report_export_failure(tmp_path, tmp_path / "absent.txt")
    assert code == 1
    assert result["errors"] == [method_check.EXPORT_FAILED]
    assert result["export_diagnostics"] == []
    assert "**Export diagnostics:** none recorded; see the export job log." in summary


def test_an_export_or_a_failed_export_is_required_not_both(tmp_path: Path) -> None:
    common = ["--revision", GIT, "--output-dir", str(tmp_path / "o")]
    with pytest.raises(SystemExit):
        method_check.main(["--export", "e.json", "--export-failed", "d.txt", *common])
    with pytest.raises(SystemExit):
        method_check.main(common)


def test_the_summary_bounds_the_export_diagnostics_and_keeps_its_fence() -> None:
    lines = [f"model.sysml:{n}:1: error (rule): message {n}" for n in range(method_check.MAX_ROWS + 5)]
    result = {"revision": "a" * 40, "export": {}, "increments": [], "notes": [],
              "errors": [method_check.EXPORT_FAILED], "export_diagnostics": ["```", *lines]}
    text = method_check.render_summary(result)
    fenced = text.split("```text\n", 1)[1].split("\n```", 1)[0].splitlines()
    assert len(fenced) == method_check.MAX_ROWS and "```" not in fenced
    assert "6 more in the JSON." in text


# -- summary rendering ---------------------------------------------------------


def test_the_summary_names_next_and_the_blocking_gaps_per_increment(tmp_path: Path, real_reports) -> None:
    export = _export(tmp_path, _gappy, _without_workflow)
    _code, result, _summary = _run(tmp_path, export, EntryPointSpy(real_reports))
    text = method_check.render_summary(result, artifact=f"method-check-{GIT}", run_id="4242",
                                       repository="de4sdv/DE4SDV")
    lines = text.splitlines()
    assert lines[0] == "## Method check"
    assert "Advisory: gaps never fail this check; only a technical error does." in text
    assert f"| `{FIRST}` | evaluated | `needHasStakeholder` (phase4_needs) | 1 | 4 |" in lines
    assert f"| `{SECOND}` | method unavailable | none | - | - |" in lines
    assert f"### `{FIRST}`" in lines
    assert "**Next:** `needHasStakeholder` in phase4_needs (violation)" in lines
    stakeholder, package = kernel_qualified_name(cut_method_builder("oracle"), "Stakeholder")
    what = (f"add to DE4SDV_FirstNeedsRequirements::need1, after its subject: stakeholder <stakeholderName> : "
            f"{stakeholder}; Import: private import {package}::*; {SUBJECT_FIRST}")
    at = lines.index(f"- What to author: `{what}`")
    assert lines[at + 1:at + 6] == ["", "  ```sysml", f"  private import {package}::*;",
                                    f"  stakeholder <stakeholderName> : {stakeholder};", "  ```"]
    assert "- Where: increment package `DE4SDV_FirstFraming`; packages `DE4SDV_FirstNeedsRequirements`" in lines
    assert "- Subjects (1): `DE4SDV_FirstNeedsRequirements::need1`" in lines
    assert "**Blocking gaps: 1** (violation: 1)" in lines
    assert "| `needHasStakeholder` | phase4_needs | violation | 1 | `need1` |" in lines
    assert ("**Phase exits:** phase0_incrementFraming READY (15/15 pass), phase4_needs BLOCKED (4/6 pass), "
            "phase5_requirements READY (4/6 pass), phase6_functionalArchitecture READY (0/4 pass, 4 not applicable), "
            "phase7_logicalArchitecture READY (0/2 pass, 2 not applicable), phase8_physicalRealization READY "
            "(0/4 pass, 4 not applicable), phase10_vvEvidence READY (2/3 pass)") in lines
    assert "<details><summary>Advisory notes: 4</summary>" in lines
    assert "| `verificationCaseHasEvidenceRecordOrStatus` | phase10_vvEvidence | method-side | 1 | `firstVerification` |" in lines
    assert f"gh run download 4242 -R de4sdv/DE4SDV -n method-check-{GIT}" in text
    assert "no acceptance, compliance or certification claim" in text


def test_a_population_finding_is_rendered_as_its_diagnostic_not_as_a_subject(tmp_path: Path, real_reports) -> None:
    # A population-policy result names no element: the engine reports one
    # subject record without an element id that carries the finding.
    export = _export(tmp_path, _overpopulated)
    _code, result, _summary = _run(tmp_path, export, EntryPointSpy(real_reports))
    entry = result["increments"][0]
    gap = entry["evaluation"]["gaps"]["blocking"][0]
    assert gap["gate"] == "incrementHasEngineeringQuestion"
    assert gap["subjects"][0]["element_id"] is None
    text = method_check.render_summary(result)
    finding = "the population has 2 subjects; the population policy allows at most 1"
    assert f"| `incrementHasEngineeringQuestion` | phase0_incrementFraming | violation | 0 | {finding} |" in text
    assert f"- Finding: {finding}" in text
    assert "`?`" not in text and "Subjects (1)" not in text


def test_the_summary_bounds_subjects_and_escapes_table_cells() -> None:
    subjects = [{"name": f"need|{i}", "qualified_name": f"P::need|{i}"} for i in range(5)]
    gap = {"gate": "needHasStakeholder", "phase": "phase4_needs", "kind": "violation", "subjects": subjects}
    entry = {
        "id": "INC-AEBS-010", "outcome": "evaluated", "usage": {"qualified_name": "P::inc"}, "charters": [],
        "next": {"gate": "needHasStakeholder", "stage": "phase4_needs", "kind": "violation",
                 "what_to_author": "add `x`", "where": {}, "subjects": subjects},
        "next_reason": "", "counts": {"blocking": 1, "blocking_by_kind": {"violation": 1}, "advisory": 0},
        "phase_exits": {}, "diagnostics": [],
        "evaluation": {"gaps": {"blocking": [gap], "advisory": []}, "next": {"method_side_blockers": []}},
    }
    result = {"revision": "a" * 40, "export": {}, "increments": [entry], "notes": [], "errors": []}
    text = method_check.render_summary(result)
    assert "| `needHasStakeholder` | phase4_needs | violation | 5 | `need\\|0`, `need\\|1`, `need\\|2` (+2 more) |" in text
    assert "- Subjects (5): `P::need|0`, `P::need|1`, `P::need|2` (+2 more)" in text
    assert "- What to author: `add 'x'`" in text


def test_the_summary_reports_a_model_without_increments() -> None:
    result = {"revision": "a" * 40, "export": {}, "increments": [], "notes": [], "errors": []}
    text = method_check.render_summary(result)
    assert "The model declares no increment" in text


# -- the real entry point --------------------------------------------------------


def test_the_entry_point_evaluates_every_increment_of_a_synthetic_export(tmp_path: Path) -> None:
    """No spy: discovery, then ``scripts/evaluate_increment.py`` in its own process per increment."""
    export = _export(tmp_path, _gappy, _without_workflow)
    code, result, summary = _run(tmp_path, export, method_check.subprocess_runner)
    assert code == 0, result["errors"]
    by_id = {entry["id"]: entry for entry in result["increments"]}
    assert by_id[FIRST]["outcome"] == "evaluated"
    assert by_id[FIRST]["next"]["gate"] == "needHasStakeholder"
    assert by_id[FIRST]["evaluation"]["schema"] == "de4sdv-increment-evaluation/v1"
    assert by_id[FIRST]["evaluation"]["identity_mode"] == "export-validated-kernel-bindings"
    assert by_id[SECOND]["outcome"] == "method-unavailable"
    assert (tmp_path / "result" / f"{FIRST}.json").is_file()
    assert (tmp_path / "result" / "method-check.md").read_text() in summary
    assert "`needHasStakeholder`" in summary


def test_declared_phases_without_executable_checks_are_reported_never_dropped(tmp_path: Path) -> None:
    """0 blocking says nothing about a declared phase that no check judges: the report names those phases
    and what their steps declare, apart from the evaluated phase exits."""
    export = _export(tmp_path, _declares_unchecked_phases)
    code, result, summary = _run(tmp_path, export, method_check.subprocess_runner)
    assert code == 0, result["errors"]
    (entry,) = result["increments"]
    assert (entry["counts"]["blocking"], entry["next"]) == (0, None)
    # The evaluated exits only: phases 6 to 8 have checks, not applicable to an increment that does not
    # declare them.
    assert list(entry["phase_exits"]) == [P0, P4, P5, "phase6_functionalArchitecture", "phase7_logicalArchitecture",
                                          "phase8_physicalRealization", P10]
    assert entry["phases_without_checks"] == [
        {"phase": P1, "step": "frameConcerns", "outputs": ["stakeholders", "concerns"]},
        {"phase": P2, "step": "specifyOperationalContext", "outputs": ["operationalContext"]},
    ]
    lines = summary.splitlines()
    assert ("**Declared phases without executable checks at this revision** (reported, never evaluated; the "
            "counts above say nothing about them): phase1_concernFraming (frameConcerns: stakeholders, concerns), "
            "phase2_operationalContext (specifyOperationalContext: operationalContext)") in lines
    assert ("**Next:** none. every required gate passes or is not applicable; no executable checks at this revision "
            "judge the declared phases phase1_concernFraming, phase2_operationalContext") in lines


def test_an_increment_without_identifier_is_reported_as_not_evaluated(tmp_path: Path, real_reports) -> None:
    """Owner decision D14: a charter's increment the method cannot identify is listed as not evaluated,
    with the reason, beside the evaluated increments; it is reported, never a technical error."""
    export = _export(tmp_path, _gappy, _legacy_increment)
    code, result, summary = _run(tmp_path, export, EntryPointSpy(real_reports))
    assert code == 0 and result["errors"] == []
    assert [entry["id"] for entry in result["increments"]] == [FIRST]
    (legacy,) = result["not_evaluated"]
    assert (legacy["outcome"], legacy["usage"]["qualified_name"]) == (
        "not-evaluated", "DE4SDV_FirstFraming::incLegacy")
    assert [charter["qualified_name"] for charter in legacy["charters"]] == ["DE4SDV_FirstFraming::legacyCharter"]
    assert legacy["reason"].startswith("its increment usage carries no increment identifier")
    assert any("legacyCharter" in note for note in result["notes"])  # the JSON keeps the note
    lines = summary.splitlines()
    assert "| `incLegacy` | not evaluated | - | - | - |" in lines  # "none" would read as "no open check"
    assert "### `incLegacy` (not evaluated)" in lines
    assert ("Increment usage `DE4SDV_FirstFraming::incLegacy`; charter `DE4SDV_FirstFraming::legacyCharter`"
            in lines)
    assert ("**Not evaluated:** its increment usage carries no increment identifier (INC-&lt;SUBJECT&gt;-&lt;SEQ&gt;) "
            "as its declared short name, and the method finds an increment only by that short name") in lines
    assert not any(line.startswith("- charter") for line in lines)  # not repeated among the notes
    assert ", 1 increment, 1 not evaluated" in summary
