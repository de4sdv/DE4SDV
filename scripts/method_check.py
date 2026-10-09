#!/usr/bin/env python3
"""Method check of one revision: every increment the model declares, evaluated offline.

Reads a full-model JSON export of one revision, finds the increments the model
declares (through their charters and short names; none is named here), runs
the evaluation entry point ``scripts/evaluate_increment.py`` once per
increment, and writes:

- ``<output-dir>/method-check.json``: per increment, ``next`` (the first
  check the agent can act on), the gap counts, the phase exits and the full
  entry-point report under ``evaluation``;
- ``<output-dir>/<increment id>.json``: each entry-point report;
- ``<output-dir>/method-check.md``: a readable summary, also appended to
  ``--summary`` (for example ``$GITHUB_STEP_SUMMARY``) and printed.

    python scripts/method_check.py --export model-export.json \\
        --revision <40-hex commit> --output-dir method-check \\
        [--summary "$GITHUB_STEP_SUMMARY"] [--artifact method-check-<commit>]

Advisory: gaps never fail the check (owner decision 3: the delivery gate stays
advisory). Exit code 1 only for a technical error: an unreadable or refused
export, an export of another revision, increments that cannot be identified,
an entry point that refuses or fails, or a method that cannot be read (an
invalid workflow). Read-only; no API or network.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping, NamedTuple, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic import method_evaluator as me  # noqa: E402
from de4sdv.semantic.export_evaluation import (  # noqa: E402
    ExportEvaluationRefused,
    export_view,
    load_export_snapshot,
)
from de4sdv.semantic.increment_discovery import DeclaredIncrement, declared_increments  # noqa: E402
from de4sdv.sysml_api.errors import IdentityNotFoundError  # noqa: E402

ENTRY_POINT = ROOT / "scripts" / "evaluate_increment.py"
SCHEMA = "de4sdv-method-check/v1"
RESULT_FILE = "method-check.json"
SUMMARY_FILE = "method-check.md"
ENTRY_POINT_TIMEOUT_SECONDS = 900
POLICY = "advisory: gaps never fail this check; only a technical error does"
CLAIM_BOUNDARY = ("model-content checks of the method declared in the evaluated revision; "
                  "no acceptance, compliance or certification claim")

OUTCOME_EVALUATED = "evaluated"
OUTCOME_UNAVAILABLE = "method-unavailable"
OUTCOME_INVALID = "method-invalid"
OUTCOME_ERROR = "error"

#: Subjects shown per gap in the summary; the JSON carries all of them.
FIRST_SUBJECTS = 3
#: Rows per gap table in the summary; the JSON carries all of them.
MAX_ROWS = 25
_FULL_SHA = re.compile(r"\A[0-9a-f]{40}\Z")


class RunnerResult(NamedTuple):
    """What one entry-point process returned."""

    returncode: int
    stdout: str
    stderr: str


Runner = Callable[[Sequence[str]], RunnerResult]


def subprocess_runner(argv: Sequence[str]) -> RunnerResult:
    """Run the entry point in its own process (the production transport)."""
    try:
        completed = subprocess.run(list(argv), cwd=ROOT, capture_output=True, text=True,
                                   timeout=ENTRY_POINT_TIMEOUT_SECONDS, check=False)
    except subprocess.TimeoutExpired:
        return RunnerResult(-1, "", f"timed out after {ENTRY_POINT_TIMEOUT_SECONDS} seconds")
    return RunnerResult(completed.returncode, completed.stdout, completed.stderr)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def check(export: Path, revision: str, output_dir: Path, *, runner: Runner = subprocess_runner) -> dict[str, Any]:
    """Evaluate every increment the export declares; never raises on model content."""
    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "schema": SCHEMA, "revision": revision, "policy": POLICY, "claim_boundary": CLAIM_BOUNDARY,
        "export": {}, "increments": [], "notes": [], "errors": [], "timings": {},
    }
    try:
        snapshot = load_export_snapshot(export)
    except (OSError, ValueError, KeyError, TypeError, ExportEvaluationRefused) as error:
        result["errors"].append(f"the export cannot be read: {error}")
        return result
    result["export"] = {
        "git_commit": snapshot.revision.git_commit, "sha256": snapshot.export_sha256,
        "element_count": len(snapshot.elements), "identity_mode": snapshot.identity_mode,
        "semantic_authority": snapshot.semantic_authority_id,
    }
    if snapshot.revision.git_commit != revision:
        result["errors"].append(
            f"the export is of revision {snapshot.revision.git_commit or '(none)'}, not of {revision}")
        return result
    try:
        discovery = declared_increments(export_view(snapshot))
    except IdentityNotFoundError as error:
        result["errors"].append(f"the declared increments cannot be identified: {error}")
        return result
    del snapshot  # each entry-point process loads the export itself
    result["notes"] = list(discovery.notes)
    result["timings"]["discovery_seconds"] = round(time.perf_counter() - started, 3)
    for increment in discovery.increments:
        entry, errors = _evaluate(increment, export, output_dir, runner)
        result["increments"].append(entry)
        result["errors"].extend(errors)
    result["timings"]["total_seconds"] = round(time.perf_counter() - started, 3)
    return result


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _tail(text: str, lines: int = 20) -> str:
    return " | ".join(line for line in text.strip().splitlines()[-lines:] if line.strip())


def _evaluate(increment: DeclaredIncrement, export: Path, output_dir: Path,
              runner: Runner) -> tuple[dict[str, Any], list[str]]:
    identifier = increment.increment_id
    report_path = output_dir / f"{identifier}.json"
    argv = [sys.executable, str(ENTRY_POINT), "--export", str(export), "--increment", identifier,
            "--query", "all", "--output", str(report_path)]
    entry: dict[str, Any] = {
        "id": identifier, "outcome": OUTCOME_ERROR, "usage": dict(increment.usage),
        "charters": [dict(charter) for charter in increment.charters], "report": report_path.name,
        "next": None, "next_reason": "", "counts": {}, "phase_exits": {}, "diagnostics": [],
        "evaluation": None,
    }
    report_path.unlink(missing_ok=True)  # never read a report an earlier run left behind
    run = runner(argv)
    report = _read_json(report_path)
    if run.returncode != 0 or report is None or report.get("status") == "refused":
        if run.returncode == 2 and report is not None:
            detail = str(report.get("reason") or "refused")
            verb = "refused the evaluation"
        else:
            detail = _tail(run.stderr) or _tail(run.stdout) or "no report was written"
            verb = "failed"
        entry["diagnostics"] = [detail]
        return entry, [f"{identifier}: the evaluation entry point {verb} (exit code {run.returncode}): {detail}"]

    entry["evaluation"] = report
    status = report.get("status") or {}
    next_block = report.get("next") or {}
    resolution = list(((status.get("increment") or {}).get("diagnostics")) or [])
    available = status.get("executable_contract_available") is not False
    # An invalid workflow is an evaluation ERROR without an executable method;
    # a gate error under a readable method is model feedback, reported in the gaps.
    if me.INVALID_CONTRACT in (status.get("reason_codes") or []) or (
            not available and status.get("evaluation_state") == me.STATE_ERROR):
        problems = list((status.get("method") or {}).get("problems") or [])
        entry["outcome"] = OUTCOME_INVALID
        entry["diagnostics"] = [*(status.get("diagnostics") or []), *problems]
        return entry, [f"{identifier}: the method cannot be read: {'; '.join(entry['diagnostics'])}"]
    if not available:
        entry["outcome"] = OUTCOME_UNAVAILABLE
        entry["diagnostics"] = [*(status.get("diagnostics") or []), *resolution]
        entry["next_reason"] = str(next_block.get("reason") or "")
        return entry, []
    gaps = report.get("gaps") or {}
    entry["outcome"] = OUTCOME_EVALUATED
    entry["next"] = next_block.get("next")
    entry["next_reason"] = str(next_block.get("reason") or "")
    entry["counts"] = {
        "blocking": len(gaps.get("blocking") or []),
        "blocking_by_kind": dict(gaps.get("counts") or {}),
        "advisory": len(gaps.get("advisory") or []),
        "method_side_blockers": len(next_block.get("method_side_blockers") or []),
    }
    entry["phase_exits"] = {phase["phase"]: phase.get("phase_exit") for phase in status.get("phases") or []}
    entry["diagnostics"] = [*(status.get("diagnostics") or []), *resolution]
    return entry, []


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def _code(text: Any, *, cell: bool = False) -> str:
    value = " ".join(str(text).split()).replace("`", "'")
    if cell:
        value = value.replace("|", "\\|")
    return f"`{value}`"


def _plain(text: Any, *, cell: bool = False) -> str:
    value = " ".join(str(text).split())
    value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if cell:
        value = value.replace("|", "\\|")
    return value


def _subject_label(subject: Mapping[str, Any], *, qualified: bool) -> str:
    keys = ("qualified_name", "name") if qualified else ("name", "qualified_name")
    for key in (*keys, "element_id"):
        if subject.get(key):
            return str(subject[key])
    return ""


def _split_subjects(records: Sequence[Mapping[str, Any]]) -> tuple[list[Mapping[str, Any]], list[str]]:
    """Element subjects, and the findings of records that name no element.

    A population-policy result (too many or no subjects) is reported as one
    record without an element; its diagnostics are the finding.
    """
    subjects = [r for r in records if _subject_label(r, qualified=False)]
    findings: list[str] = []
    for record in records:
        if record in subjects:
            continue
        for diagnostic in record.get("diagnostics") or []:
            if diagnostic not in findings:
                findings.append(str(diagnostic))
    return subjects, findings


def _first_subjects(subjects: Sequence[Mapping[str, Any]], *, qualified: bool, cell: bool) -> str:
    shown = ", ".join(_code(_subject_label(s, qualified=qualified), cell=cell) for s in subjects[:FIRST_SUBJECTS])
    more = len(subjects) - FIRST_SUBJECTS
    return f"{shown} (+{more} more)" if more > 0 else shown


def _gap_table(gaps: Sequence[Mapping[str, Any]]) -> list[str]:
    lines = ["| Check | Phase | Kind | Subjects | First subjects |", "| --- | --- | --- | ---: | --- |"]
    for gap in gaps[:MAX_ROWS]:
        subjects, findings = _split_subjects(list(gap.get("subjects") or []))
        findings += [str(item) for item in (gap.get("diagnostics") or gap.get("missing") or [])]
        first = (_first_subjects(subjects, qualified=False, cell=True) if subjects
                 else _plain("; ".join(findings) or "-", cell=True))
        lines.append(f"| {_code(gap.get('gate'), cell=True)} | {_plain(gap.get('phase'), cell=True)} | "
                     f"{_plain(gap.get('kind'), cell=True)} | {len(subjects)} | {first} |")
    if len(gaps) > MAX_ROWS:
        lines.append(f"\n{len(gaps) - MAX_ROWS} more in the JSON.")
    return lines


def _overview_row(entry: Mapping[str, Any]) -> str:
    outcome = str(entry.get("outcome") or "").replace("-", " ")
    step = entry.get("next")
    counts = entry.get("counts") or {}
    if entry.get("outcome") == OUTCOME_EVALUATED:
        next_text = f"{_code(step.get('gate'), cell=True)} ({_plain(step.get('stage'), cell=True)})" if step else "none"
        blocking, advisory = str(counts.get("blocking", 0)), str(counts.get("advisory", 0))
    else:
        next_text, blocking, advisory = "none", "-", "-"
    return f"| {_code(entry.get('id'), cell=True)} | {_plain(outcome, cell=True)} | {next_text} | {blocking} | {advisory} |"


def _increment_section(entry: Mapping[str, Any]) -> list[str]:
    lines = [f"### {_code(entry.get('id'))}", ""]
    usage = (entry.get("usage") or {}).get("qualified_name")
    charters = [c.get("qualified_name") for c in entry.get("charters") or [] if c.get("qualified_name")]
    header = f"Increment {_code(usage)}" if usage else "Increment usage not resolved"
    header += f"; charter {', '.join(_code(c) for c in charters)}" if charters else "; no charter"
    lines += [header, ""]
    outcome = entry.get("outcome")
    diagnostics = list(entry.get("diagnostics") or [])
    if outcome != OUTCOME_EVALUATED:
        label = {OUTCOME_UNAVAILABLE: "Method unavailable", OUTCOME_INVALID: "Method invalid (technical error)",
                 OUTCOME_ERROR: "Evaluation failed (technical error)"}.get(str(outcome), str(outcome))
        lines.append(f"**{label}:** {_plain('; '.join(diagnostics) or 'no diagnostic')}")
        return lines + [""]

    step = entry.get("next")
    if step:
        lines.append(f"**Next:** {_code(step.get('gate'))} in {_plain(step.get('stage'))} ({_plain(step.get('kind'))})")
        if step.get("what_to_author"):
            lines.append(f"- What to author: {_code(step['what_to_author'])}")
        where = step.get("where") or {}
        places = []
        if (where.get("increment_package") or {}).get("qualified_name"):
            places.append(f"increment package {_code(where['increment_package']['qualified_name'])}")
        if where.get("packages"):
            places.append(f"packages {', '.join(_code(p) for p in where['packages'])}")
        if places:
            lines.append(f"- Where: {'; '.join(places)}")
        subjects, findings = _split_subjects(list(step.get("subjects") or []))
        if subjects:
            lines.append(f"- Subjects ({len(subjects)}): {_first_subjects(subjects, qualified=True, cell=False)}")
        if findings:
            lines.append(f"- Finding: {_plain('; '.join(findings))}")
    else:
        lines.append(f"**Next:** none. {_plain(entry.get('next_reason') or '')}".rstrip())
    lines.append("")

    evaluation = entry.get("evaluation") or {}
    blocking = list((evaluation.get("gaps") or {}).get("blocking") or [])
    by_kind = (entry.get("counts") or {}).get("blocking_by_kind") or {}
    kinds = ", ".join(f"{kind}: {count}" for kind, count in sorted(by_kind.items()))
    lines.append(f"**Blocking gaps: {len(blocking)}**" + (f" ({kinds})" if kinds else ""))
    if blocking:
        lines += [""] + _gap_table(blocking)
    lines.append("")
    method_side = list((evaluation.get("next") or {}).get("method_side_blockers") or [])
    if method_side:
        lines.append("**Method-side blockers** (need a method or kernel change, not authoring): "
                     + ", ".join(_code(item.get("gate")) for item in method_side))
        lines.append("")
    exits = entry.get("phase_exits") or {}
    if exits:
        lines.append("**Phase exits:** " + ", ".join(f"{_plain(p)} {_plain(r)}" for p, r in exits.items()))
        lines.append("")
    if diagnostics:
        lines.append("Resolution notes: " + _plain("; ".join(diagnostics)))
        lines.append("")
    advisory = list((evaluation.get("gaps") or {}).get("advisory") or [])
    if advisory:
        lines += [f"<details><summary>Advisory notes: {len(advisory)}</summary>", ""] + _gap_table(advisory)
        lines += ["", "</details>", ""]
    return lines


def render_summary(result: Mapping[str, Any], *, artifact: str | None = None, run_id: str | None = None,
                   repository: str | None = None) -> str:
    """The readable summary of one method-check result (deterministic)."""
    revision = str(result.get("revision") or "")
    export = result.get("export") or {}
    increments = list(result.get("increments") or [])
    lines = ["## Method check", "",
             "Advisory: gaps never fail this check; only a technical error does. Model-content checks of the "
             "method declared in the evaluated revision; no acceptance, compliance or certification claim.", ""]
    facts = [f"Revision {_code(revision[:12])}"]
    if export.get("sha256"):
        facts.append(f"export sha256 {_code(str(export['sha256'])[:12])}")
    if export.get("element_count") is not None:
        facts.append(f"{export['element_count']} elements")
    facts.append(f"{len(increments)} increment{'s' if len(increments) != 1 else ''}")
    lines += [", ".join(facts), ""]

    errors = list(result.get("errors") or [])
    if errors:
        lines.append(f"**Technical error{'s' if len(errors) != 1 else ''}** (the check fails):")
        lines += [f"- {_plain(error)}" for error in errors] + [""]

    if increments:
        lines += ["| Increment | Outcome | Next | Blocking | Advisory |", "| --- | --- | --- | ---: | ---: |"]
        lines += [_overview_row(entry) for entry in increments] + [""]
        for entry in increments:
            lines += _increment_section(entry)
    elif not errors:
        lines += ["The model declares no increment: no charter references an increment usage and no "
                  "increment usage carries an increment identifier.", ""]

    notes = list(result.get("notes") or [])
    if notes:
        lines.append("**Notes**")
        lines += [f"- {_plain(note)}" for note in notes[:MAX_ROWS]]
        if len(notes) > MAX_ROWS:
            lines.append(f"- {len(notes) - MAX_ROWS} more in the JSON.")
        lines.append("")
    if artifact:
        hint = f"Full JSON: artifact {_code(artifact)}"
        if run_id:
            command = f"gh run download {run_id}" + (f" -R {repository}" if repository else "") + f" -n {artifact}"
            hint += f" ({_code(command)})"
        lines += [hint + ".", ""]
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def _full_commit(value: str) -> str:
    if not _FULL_SHA.fullmatch(value):
        raise argparse.ArgumentTypeError(f"{value!r} is not a full 40-character lowercase commit id")
    return value


def main(argv: Sequence[str] | None = None, *, runner: Runner = subprocess_runner) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--export", type=Path, required=True, help="full-model JSON export of the revision")
    parser.add_argument("--revision", type=_full_commit, required=True,
                        help="the full commit id the export must be of")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--summary", type=Path, help="Markdown file the summary is appended to")
    parser.add_argument("--artifact", help="name of the artifact that carries the output directory")
    args = parser.parse_args(argv)

    result = check(args.export, args.revision, args.output_dir, runner=runner)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / RESULT_FILE).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    summary = render_summary(result, artifact=args.artifact, run_id=os.environ.get("GITHUB_RUN_ID"),
                             repository=os.environ.get("GITHUB_REPOSITORY"))
    (args.output_dir / SUMMARY_FILE).write_text(summary, encoding="utf-8")
    if args.summary is not None:
        with args.summary.open("a", encoding="utf-8") as handle:
            handle.write(summary)
    print(summary)
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
