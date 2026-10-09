"""The pull-request method check: every declared increment, evaluated offline.

``scripts/method_check.py`` discovers the increments of an export (through
charters and short names), runs the evaluation entry point
``scripts/evaluate_increment.py`` once per increment, and writes one JSON
result plus a readable summary. Gaps never fail it; technical errors do.

Synthetic export-shaped fixtures only; no network. A transport spy stands in
for the entry-point process where a test only checks orchestration; one test
runs the real entry point.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from increment_model_fixtures import (
    ModelBuilder,
    WorkflowCheck,
    increment_scenario,
    increment_workflow,
    install_model_workflow,
    model_workflow_steps,
)
from scripts import method_check

ROOT = Path(__file__).resolve().parents[1]
GIT = "e" * 40
FIRST, SECOND, THIRD, FOURTH = "INC-FIXTURE-001", "INC-FIXTURE-002", "INC-FIXTURE-003", "INC-FIXTURE-004"


def _gappy(builder: ModelBuilder) -> None:
    """First: the model workflow, one need without a stakeholder (one blocking gap)."""
    first = increment_scenario(builder, increment_id=FIRST, name="First")
    install_model_workflow(first)
    need = first.needs[1]
    builder.remove(*[e for e in builder.elements if e.get("@type") == "StakeholderMembership"
                     and e.get("owningRelatedElement", {}).get("@id") == need["@id"]])


def _without_workflow(builder: ModelBuilder) -> None:
    """Second: a charter that declares no workflow (the method is unavailable)."""
    increment_scenario(builder, increment_id=SECOND, name="Second")


def _invalid_workflow(builder: ModelBuilder) -> None:
    """Third: a workflow with an unknown check id (the method is invalid)."""
    third = increment_scenario(builder, increment_id=THIRD, name="Third")
    steps = model_workflow_steps(third)
    steps[0] = replace(steps[0], checks=steps[0].checks + (
        WorkflowCheck("incrementHasNothing", "noSuchCheck", "increment"),))
    increment_workflow(builder, steps, charter=third.charter, package_name="DE4SDV_ThirdWorkflow")


def _overpopulated(builder: ModelBuilder) -> None:
    """Fourth: two engineering questions where the workflow allows exactly one (a population finding)."""
    fourth = increment_scenario(builder, increment_id=FOURTH, name="Fourth")
    increment_workflow(builder, model_workflow_steps(fourth), charter=fourth.charter,
                       package_name="DE4SDV_FourthWorkflow")
    builder.usage("PartUsage", "fourthSecondQuestion", fourth.framing,
                  [builder.kernel_definition("IncrementEngineeringQuestion")])


def _export(tmp_path: Path, *parts, git_commit: str = GIT) -> Path:
    builder = ModelBuilder(label="method-check")
    for part in parts:
        part(builder)
    path = tmp_path / "model-export.json"
    path.write_text(json.dumps(builder.export(git_commit=git_commit)))
    return path


@pytest.fixture(scope="module")
def real_reports(tmp_path_factory) -> dict[str, dict]:
    """One real entry-point report per outcome, evaluated in process once."""
    import importlib.util

    tmp_path = tmp_path_factory.mktemp("reports")
    export = _export(tmp_path, _gappy, _without_workflow, _invalid_workflow, _overpopulated)
    spec = importlib.util.spec_from_file_location("evaluate_increment", ROOT / "scripts/evaluate_increment.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    reports = {}
    for increment in (FIRST, SECOND, THIRD, FOURTH):
        code, report, _output = module.run(["--export", str(export), "--increment", increment])
        assert code == 0
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
    assert entry["counts"]["advisory"] == 3
    assert entry["next"]["gate"] == "needHasStakeholder"
    assert entry["next"]["stage"] == "phase4_needs"
    assert entry["phase_exits"]["phase4_needs"] == "BLOCKED"
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


@pytest.mark.parametrize("code, expected", [(2, "refused by the spy"), (1, "Traceback: boom")])
def test_a_refused_or_crashed_evaluation_is_a_technical_error(tmp_path: Path, real_reports, code, expected):
    export = _export(tmp_path, _gappy, _without_workflow)
    spy = EntryPointSpy(real_reports, codes={SECOND: code}, stderr="Traceback: boom")
    exit_code, result, summary = _run(tmp_path, export, spy)
    assert exit_code == 1
    assert len(spy.calls) == 2  # one failure never skips the other increments
    outcomes = {entry["id"]: entry["outcome"] for entry in result["increments"]}
    assert outcomes == {FIRST: "evaluated", SECOND: "error"}
    assert any(SECOND in error and expected in error for error in result["errors"])
    assert expected in summary


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


def test_an_unbound_increment_lineage_is_a_technical_error(tmp_path: Path, real_reports) -> None:
    builder = ModelBuilder(label="method-check")
    _gappy(builder)
    export = builder.export(git_commit=GIT)
    export["element_sources"][builder.kernel["EngineeringIncrement"]["@id"]] = "elsewhere.sysml"
    path = tmp_path / "model-export.json"
    path.write_text(json.dumps(export))
    spy = EntryPointSpy(real_reports)
    code, result, _summary = _run(tmp_path, path, spy)
    assert code == 1
    assert spy.calls == []
    assert any("EngineeringIncrement" in error for error in result["errors"])


def test_the_revision_must_be_a_full_commit_id(tmp_path: Path, real_reports) -> None:
    export = _export(tmp_path, _gappy)
    with pytest.raises(SystemExit):
        method_check.main(["--export", str(export), "--revision", "HEAD", "--output-dir", str(tmp_path / "o")],
                          runner=EntryPointSpy(real_reports))


# -- summary rendering ---------------------------------------------------------


def test_the_summary_names_next_and_the_blocking_gaps_per_increment(tmp_path: Path, real_reports) -> None:
    export = _export(tmp_path, _gappy, _without_workflow)
    _code, result, _summary = _run(tmp_path, export, EntryPointSpy(real_reports))
    text = method_check.render_summary(result, artifact=f"method-check-{GIT}", run_id="4242",
                                       repository="de4sdv/DE4SDV")
    lines = text.splitlines()
    assert lines[0] == "## Method check"
    assert "Advisory: gaps never fail this check; only a technical error does." in text
    assert f"| `{FIRST}` | evaluated | `needHasStakeholder` (phase4_needs) | 1 | 3 |" in lines
    assert f"| `{SECOND}` | method unavailable | none | - | - |" in lines
    assert f"### `{FIRST}`" in lines
    assert "**Next:** `needHasStakeholder` in phase4_needs (violation)" in lines
    assert "- What to author: `add to DE4SDV_FirstNeedsRequirements::need1: stakeholder <name> : <role>;`" in lines
    assert "- Where: increment package `DE4SDV_FirstFraming`; packages `DE4SDV_FirstNeedsRequirements`" in lines
    assert "- Subjects (1): `DE4SDV_FirstNeedsRequirements::need1`" in lines
    assert "**Blocking gaps: 1** (violation: 1)" in lines
    assert "| `needHasStakeholder` | phase4_needs | violation | 1 | `need1` |" in lines
    assert ("**Phase exits:** phase0_incrementFraming READY, phase4_needs BLOCKED, "
            "phase5_requirements READY, phase10_vvEvidence READY") in lines
    assert "<details><summary>Advisory notes: 3</summary>" in lines
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
