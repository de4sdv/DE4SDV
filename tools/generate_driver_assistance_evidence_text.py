#!/usr/bin/env python3
"""Write the phase 10 evidence text of INC-DRIVING-002 (slice 10b) from the case evaluators' outputs.

Usage::

    python tools/generate_driver_assistance_evidence_text.py \\
        --verdicts verdicts.json --records records.json [--analysis-039 analysis_039.json] [--check]

The inputs are the outputs of the case evaluators of the driver-assistance bench
(``implementation/driver-assistance-bench/case-evaluators/``): ``evaluate_da_campaign.py``
writes ``verdicts.json`` and ``evidence_record.py`` writes ``records.json`` for the same
session. ``analysis_039.json`` is the desk analysis of REQ-DRIVING-039: the six attributes
of ``RetainedCommandFormAnalysis``, an ``outcome`` (a literal of
``AssistanceEvidenceOutcome``) and optionally a ``reason``.

The script patches
``textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml``
in place and changes nothing else in the package:

- one ``item`` usage of ``RetainedAssistanceRunEvidence`` per run, after ``item def
  RetainedCommandFormAnalysis``, binding every attribute of the definition in its order
  (``attribute :>> <name> = "<value>";``; the two enumeration-typed attributes bind the
  model's literals), with a doc that starts with its ``EVID-DRIVING-NNN`` identity and
  names every empty attribute, which stays unbound (``attribute :>> <name>;``);
- one ``item`` usage of ``RetainedCommandFormAnalysis`` when the analysis is given;
- in the doc of each case usage VC-DRIVING-036 to VC-DRIVING-044, a status paragraph in
  place of "Not started.": the outcome literal, the verdict, the session, the criteria
  record and the evaluator revision, each run read by its run identity with the record
  usage it reads, its outcome and the values measured with their units, and the reason
  when the verdict is inconclusive or error. VC-DRIVING-039 gets one only with the analysis.

Identities: the script greps ``textual-notation-of-model/`` and ``tests/`` for
``EVID-DRIVING-NNN``; a record usage it wrote before keeps its identity (by its name), a
new one takes the next number after the highest found, and the sequence starts at 001
when there is none. It refuses a rehearsal session and inputs that disagree (exit 3),
wraps every doc it writes at 80 columns without splitting an identifier, and checks
before writing that the comment-stripped code differs from the input only by the record
usages. A second run on the same inputs changes nothing; ``--check`` exits 1 when the
file is not what the inputs give.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODEL = (REPO / "textual-notation-of-model" / "packages" / "features" / "driving"
         / "driver_assistance_verification_evidence.sysml")
SCAN_ROOTS = ("textual-notation-of-model", "tests")
PREFIX = "EVID-" + "DRIVING-"          # split so that this file holds no identity
IDENTITY_RE = re.compile(re.escape(PREFIX) + r"(\d{3})")
RUN_DEF = "RetainedAssistanceRunEvidence"
ANALYSIS_DEF = "RetainedCommandFormAnalysis"
SCENARIO_ENUM = "AssistanceScenarioIdentity"
SETTING_ENUM = "AssistanceSettingIdentity"
OUTCOME_ENUM = "AssistanceEvidenceOutcome"
VERDICT_CALC = "MapAssistanceEvidenceOutcomeToVerdict"
VERDICTS_SCHEMA = "de4sdv.driving.da-campaign-verdicts.v1"
RECORDS_SCHEMA = "de4sdv.driving.retained-assistance-run-evidence.v1"
RECORD_COMPLETE = "complete"
INCONCLUSIVE = "inconclusiveMissingEvidence"
CASES = tuple(f"VC-DRIVING-{n:03d}" for n in range(36, 45))
ANALYSIS_CASE = "VC-DRIVING-039"
ANALYSIS_NAME = "commandFormAnalysisEvidence"
STOP_NAME = "pathStoppedRunEvidence"
HEADER = ("Evidence records: one RetainedAssistanceRunEvidence per run of the judged session and the "
          "RetainedCommandFormAnalysis of VC-DRIVING-039, written by "
          "tools/generate_driver_assistance_evidence_text.py from the case evaluators' outputs; "
          "regenerate them, never edit them by hand.")
NOT_STARTED = "Not started."
STATUS_START = "Outcome: "
# The evaluators name a setting by scenario and speed and a scenario by its id; the model names
# them by the literals that the docs of the two enumerations map them to.
SETTING_LITERALS = {
    "SC-DRIVING-012@20": "stationaryAt20", "SC-DRIVING-012@42": "stationaryAt42",
    "SC-DRIVING-012@60": "stationaryAt60", "SC-DRIVING-013@30": "slowerAt30",
    "SC-DRIVING-013@60": "slowerAt60", "SC-DRIVING-014@30": "curveAt30",
    "SC-DRIVING-015@40": "turningOffAt40",
}
SCENARIO_LITERALS = {
    "SC-DRIVING-012": "stationaryTarget", "SC-DRIVING-013": "slowerTarget",
    "SC-DRIVING-014": "curveWithGuardPipes", "SC-DRIVING-015": "vehicleTurningOff",
}
ORDINALS = {1: "First", 2: "Second", 3: "Third", 4: "Fourth", 5: "Fifth", 6: "Sixth"}
# The unit of a measured value, by the suffix of its key in verdicts.json (longest first).
UNIT_SUFFIXES = (("Mps2", "m/s²"), ("Mps", "m/s"), ("Kmh", "km/h"), ("SimS", "s of simulation time"),
                 ("Ns", "ns"), ("Bytes", "B"), ("Deg", "deg"), ("S", "s"), ("M", "m"))
# Keys whose unit their name does not carry: cases_da.py writes functionalPart as
# [startSimS, endSimS].
KEY_UNITS = {"functionalPart": "s of simulation time"}
# Run-entry values that are no measurement of the criterion: the recorded guidance of
# SC-DRIVING-014 and -015, the stop record and the diagnosis with the dropped-image rule set aside.
SKIPPED_KEYS = ("guidance", "stopRecord", "withoutDropRule")
DOC_WIDTH = 80


class InputError(Exception):
    """The inputs cannot be written into the model: refused, inconsistent or not expressible."""


@dataclass
class Result:
    text: str
    identities: dict = field(default_factory=dict)
    allocation: str = ""


# ---------------------------------------------------------------- reading the model text
def code_mask(text: str) -> str:
    """The text with comments, notes and string contents blanked; newlines and positions kept."""
    out, i, n = list(text), 0, len(text)
    while i < n:
        if text.startswith("/*", i) or text.startswith("//*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
        elif text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
        elif text[i] == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            for p in range(i + 1, min(j, n)):
                if out[p] != "\n":
                    out[p] = "_"
            i = j + 1
            continue
        else:
            i += 1
            continue
        for p in range(i, j):
            if out[p] != "\n":
                out[p] = " "
        i = j
    return "".join(out)


def strip_comments(text: str) -> str:
    """The code: comments and notes removed, strings kept."""
    masked = code_mask(text)
    return "".join(t for t, m in zip(text, masked) if m != " " or t.isspace())


def code_tokens(text: str) -> list[str]:
    """The code as whitespace-separated tokens: comment bodies dropped, strings kept."""
    masked = code_mask(text)
    kept = "".join(t if (m != " " or t.isspace()) else " " for t, m in zip(text, masked))
    return kept.split()


def _close(masked: str, opening: int) -> int:
    depth = 0
    for k in range(opening, len(masked)):
        if masked[k] == "{":
            depth += 1
        elif masked[k] == "}":
            depth -= 1
            if depth == 0:
                return k
    raise InputError("the model text has an unbalanced brace")


def _block(text: str, masked: str, pattern: str) -> tuple[int, int]:
    found = list(re.finditer(pattern, masked, re.M))
    if len(found) != 1:
        raise InputError(f"the model text holds {len(found)} matches of {pattern!r}, not one")
    m = found[0]
    return m.start(), _close(masked, m.end() - 1) + 1


def definition_attributes(text: str, definition: str) -> list[tuple[str, str]]:
    """(name, type) of each attribute of `item def <definition>`, in order."""
    masked = code_mask(text)
    start, end = _block(text, masked, rf"^  item def {definition} \{{")
    body = strip_comments(text[start:end])
    return re.findall(r"^\s*attribute (\w+) : ([\w:]+)", body, re.M)


def enum_literals(text: str, enum: str) -> list[str]:
    masked = code_mask(text)
    start, end = _block(text, masked, rf"^  enum def {enum} \{{")
    return re.findall(r"^\s*(\w+);", strip_comments(text[start:end]), re.M)


def verdict_map(text: str) -> tuple[dict, str]:
    """The outcome-to-verdict map of `calc def MapAssistanceEvidenceOutcomeToVerdict` and its else."""
    masked = code_mask(text)
    start, end = _block(text, masked, rf"^  calc def {VERDICT_CALC} \{{")
    body = " ".join(text[start:end].split())
    pairs = dict(re.findall(rf"outcome == {OUTCOME_ENUM}::(\w+)\? VerdictKind::(\w+)", body))
    other = re.search(r"else VerdictKind::(\w+);", body)
    if not pairs or not other:
        raise InputError(f"calc def {VERDICT_CALC} has no readable map")
    return pairs, other.group(1)


@dataclass
class Model:
    text: str
    run_attributes: list
    analysis_attributes: list
    scenarios: list
    settings: list
    outcomes: list
    verdicts: dict
    verdict_else: str

    def verdict(self, outcome: str) -> str:
        return self.verdicts.get(outcome, self.verdict_else)


def read_model(text: str) -> Model:
    pairs, other = verdict_map(text)
    if INCONCLUSIVE not in enum_literals(text, OUTCOME_ENUM):
        raise InputError(f"{INCONCLUSIVE} is no literal of enum def {OUTCOME_ENUM}")
    return Model(text, definition_attributes(text, RUN_DEF), definition_attributes(text, ANALYSIS_DEF),
                 enum_literals(text, SCENARIO_ENUM), enum_literals(text, SETTING_ENUM),
                 enum_literals(text, OUTCOME_ENUM), pairs, other)


# ---------------------------------------------------------------- the generated region
def generated_spans(text: str) -> list[tuple[int, int]]:
    """The spans of the header comment and of every package-level record usage, each with the
    blank lines after it."""
    masked = code_mask(text)
    spans = []
    for m in re.finditer(rf"^  item \w+ : (?:{RUN_DEF}|{ANALYSIS_DEF}) \{{", masked, re.M):
        spans.append((m.start(), _close(masked, m.end() - 1) + 1))
    for m in re.finditer(r"^  /\* Evidence records: ", text, re.M):
        spans.append((m.start(), text.index("*/", m.start()) + 2))
    out = []
    for start, end in sorted(spans):
        while end < len(text) and text[end] == "\n":
            end += 1
        out.append((start, end))
    return out


def existing_identities(text: str) -> dict[str, str]:
    """The identity of each record usage that the text already holds, by usage name."""
    masked = code_mask(text)
    found = {}
    for m in re.finditer(rf"^  item (\w+) : (?:{RUN_DEF}|{ANALYSIS_DEF}) \{{", masked, re.M):
        block = text[m.start():_close(masked, m.end() - 1) + 1]
        d = re.search(r"doc /\*\s*\*\s*(" + re.escape(PREFIX) + r"\d{3})\.", block)
        if d:
            found[m.group(1)] = d.group(1)
    return found


def remove_generated(text: str) -> str:
    for start, end in reversed(generated_spans(text)):
        text = text[:start] + text[end:]
    return text


def insertion_point(text: str) -> int:
    masked = code_mask(text)
    _, end = _block(text, masked, rf"^  item def {ANALYSIS_DEF} \{{")
    return end


# ---------------------------------------------------------------- identities
def scan_identities(repo: Path, model_path: Path | None) -> dict[int, list[str]]:
    """Every EVID-DRIVING number in the packages and the tests, with the files that hold it. The
    target model file is read without its generated records, whose identities are kept by name."""
    found: dict[int, list[str]] = {}
    target = model_path.resolve() if model_path is not None else None
    for root in SCAN_ROOTS:
        base = repo / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            raw = path.read_text(encoding="utf-8", errors="replace")
            if target is not None and path.resolve() == target:
                raw = remove_generated(raw)
            for number in IDENTITY_RE.findall(raw):
                found.setdefault(int(number), []).append(path.relative_to(repo).as_posix())
    return found


def allocate(names: list[str], kept: dict[str, str], taken: dict[int, list[str]]) -> tuple[dict, str]:
    identities = {n: kept[n] for n in names if n in kept}
    used = set(taken) | {int(v[-3:]) for v in identities.values()}
    nxt = max(used | {0}) + 1
    for name in names:
        if name not in identities:
            identities[name] = f"{PREFIX}{nxt:03d}"
            nxt += 1
    new = [identities[n] for n in names if n not in kept]
    if taken:
        top = max(taken)
        where = ", ".join(sorted({p for paths in taken.values() for p in paths}))
        report = (f"{len(taken)} {PREFIX}NNN identities found in textual-notation-of-model/ and tests/ "
                  f"({where}); the sequence continues after {PREFIX}{top:03d}")
    else:
        report = f"no {PREFIX}NNN identity in textual-notation-of-model/ or tests/; the sequence starts"
    report += (f"; new: {new[0]} to {new[-1]}" if new else "; new: none")
    if len(identities) > len(new):
        report += f"; kept by name: {len(identities) - len(new)}"
    return identities, report


# ---------------------------------------------------------------- inputs
def _check(cond: bool, message: str) -> None:
    if not cond:
        raise InputError(message)


@dataclass
class RunInfo:
    label: str
    kind: str
    setting: str | None
    repetition: int | None
    identity: str
    name: str


def run_infos(verdicts: dict) -> list[RunInfo]:
    infos = []
    for r in verdicts.get("runs") or []:
        label, kind = r.get("run"), r.get("kind")
        identity = r.get("runIdentity") or f"run {label}"
        if kind == "stop":
            name = STOP_NAME
        else:
            literal = SETTING_LITERALS.get(r.get("setting"))
            _check(literal is not None, f"verdicts.json run {label}: setting {r.get('setting')!r} is no literal "
                                        f"of {SETTING_ENUM}")
            _check(r.get("repetition") in ORDINALS, f"verdicts.json run {label}: repetition "
                                                    f"{r.get('repetition')!r}")
            name = f"{literal}{ORDINALS[r['repetition']]}RunEvidence"
        infos.append(RunInfo(label, kind, r.get("setting"), r.get("repetition"), identity, name))
    _check(len({i.name for i in infos}) == len(infos), "verdicts.json: two runs give the same record name")
    return infos


def validate(model: Model, verdicts: dict, records: dict, analysis: dict | None) -> list[RunInfo]:
    for name, doc in (("verdicts.json", verdicts), ("records.json", records)):
        _check(not doc.get("refused"), f"{name} refused the session: {doc.get('refused')}")
    _check(verdicts.get("schema") == VERDICTS_SCHEMA, f"verdicts.json schema {verdicts.get('schema')!r}")
    _check(records.get("schema") == RECORDS_SCHEMA, f"records.json schema {records.get('schema')!r}")
    for key in ("sessionId", "criteriaRecordIdentity", "evaluatorRevision"):
        _check(isinstance(verdicts.get(key), str) and verdicts.get(key) == records.get(key),
               f"verdicts.json and records.json disagree on {key}: {verdicts.get(key)!r}, {records.get(key)!r}")
    infos = run_infos(verdicts)
    recs = records.get("records") or {}
    _check(sorted(recs) == sorted(i.label for i in infos),
           f"records.json runs {sorted(recs)} are not the runs of verdicts.json {sorted(i.label for i in infos)}")
    if "evidenceRecords" in verdicts:
        _check(verdicts["evidenceRecords"] == recs, "verdicts.json evidenceRecords differ from records.json")
    names = [a for a, _ in model.run_attributes]
    for info in infos:
        rec = recs[info.label]
        attrs = rec.get("attributes") or {}
        _check(list(attrs) == names, f"records.json {info.label}: the attributes are not those of item def "
                                     f"{RUN_DEF}")
        # the further run's setting is left empty by the record's rule, not missing
        empty = [a for a in names if attrs[a] is None and not (a == "setting" and info.kind == "stop")]
        _check(rec.get("emptyAttributes") == empty, f"records.json {info.label}: emptyAttributes {empty}")
        _check(all(attrs[a] is None or isinstance(attrs[a], str) for a in names),
               f"records.json {info.label}: an attribute value is no string")
        _check(rec.get("outcome") == (RECORD_COMPLETE if not empty else INCONCLUSIVE),
               f"records.json {info.label}: outcome {rec.get('outcome')!r} for empty {empty}")
        _check(attrs["scenario"] is None or attrs["scenario"] in SCENARIO_LITERALS,
               f"records.json {info.label}: scenario {attrs['scenario']!r} is no literal of {SCENARIO_ENUM}")
        if info.kind == "stop":
            _check(attrs["setting"] is None, f"records.json {info.label}: the further run has a setting")
        else:
            _check(attrs["setting"] is None or attrs["setting"] in SETTING_LITERALS,
                   f"records.json {info.label}: setting {attrs['setting']!r} is no literal of {SETTING_ENUM}")
    for literal in list(SCENARIO_LITERALS.values()):
        _check(literal in model.scenarios, f"{literal} is no literal of enum def {SCENARIO_ENUM}")
    for literal in list(SETTING_LITERALS.values()):
        _check(literal in model.settings, f"{literal} is no literal of enum def {SETTING_ENUM}")
    cases = verdicts.get("cases") or {}
    _check(sorted(cases) == sorted(vc for vc in CASES if vc != ANALYSIS_CASE),
           f"verdicts.json cases {sorted(cases)}")
    labels = {i.label for i in infos}
    for vc, case in cases.items():
        _check(case.get("outcome") in model.outcomes, f"{vc}: outcome {case.get('outcome')!r}")
        _check(case.get("verdict") == model.verdict(case["outcome"]),
               f"{vc}: verdict {case.get('verdict')!r} is not {VERDICT_CALC}({case['outcome']})")
        for key in ("criteriaRecordIdentity", "evaluatorRevision"):
            _check(case.get(key) == verdicts[key], f"{vc}: {key} {case.get(key)!r} is not the session's")
        for e in read_entries(case):
            _check(e.get("run") in labels, f"{vc}: run {e.get('run')!r} is no run of the session")
            _check(e.get("outcome") in model.outcomes, f"{vc} run {e.get('run')}: outcome {e.get('outcome')!r}")
        partial = [e["run"] for e in read_entries(case) if recs[e["run"]]["outcome"] != RECORD_COMPLETE]
        _check(not (partial and model.verdict(case["outcome"]) == "pass"),
               f"{vc}: pass although it reads the partial records of {partial} (a missing or partial record "
               "gives inconclusive, never pass)")
    if analysis is not None:
        names = [a for a, _ in model.analysis_attributes]
        unknown = sorted(set(analysis) - set(names) - {"outcome", "reason"})
        _check(not unknown, f"analysis_039.json: unknown keys {unknown}")
        _check(analysis.get("outcome") in model.outcomes, f"analysis_039.json: outcome {analysis.get('outcome')!r}")
        _check(all(analysis.get(a) is None or isinstance(analysis.get(a), str) for a in names),
               "analysis_039.json: an attribute value is no string")
    return infos


def read_entries(case: dict) -> list[dict]:
    m = case.get("measured") or {}
    stop = m.get("stopClause")
    return list(m.get("runs") or []) + ([stop] if isinstance(stop, dict) and stop.get("run") else [])


# ---------------------------------------------------------------- writing text
def sysml_string(value: str) -> str:
    if any(ord(c) < 32 for c in value):
        raise InputError(f"a value holds a control character: {value[:60]!r}")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def doc_block(paragraphs: list[str], indent: int) -> list[str]:
    star = " " * (indent + 1) + "*"
    lines = [" " * indent + "doc /*"]
    for k, para in enumerate(paragraphs):
        if "*/" in para:
            raise InputError(f"a doc text would close its comment (*/): {para[:80]!r}")
        if k:
            lines.append(star)
        for line in textwrap.wrap(" ".join(para.split()), width=DOC_WIDTH - len(star) - 1,
                                  break_on_hyphens=False, break_long_words=False):
            lines.append(f"{star} {line}")
    lines.append(star + "/")
    for line in lines[1:-1]:
        if line.endswith("-"):
            raise InputError(f"a doc line ends with a hyphen: {line!r}")
    return lines


def doc_paragraphs(doc_body: str) -> list[str]:
    paras, cur = [], []
    lines = doc_body.strip("\n").split("\n")
    for line in lines:
        body = re.sub(r"^\s*\*\s?", "", line).strip()
        if not body:
            if cur:
                paras.append(" ".join(cur))
            cur = []
        elif cur and cur[-1].endswith("-"):
            cur[-1] += body
        else:
            cur.append(body)
    if cur:
        paras.append(" ".join(cur))
    return [" ".join(p.split()) for p in paras]


def number(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(round(value, 3))
    return str(value)


def unit(key: str) -> str:
    if key in KEY_UNITS:
        return KEY_UNITS[key]
    for suffix, name in UNIT_SUFFIXES:
        if key.endswith(suffix) and key[:-len(suffix)][-1:].islower():
            return name
    return ""


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def value_text(key: str, value) -> str | None:
    u = unit(key)
    if isinstance(value, bool) or _is_number(value):
        return f"{key} {number(value)}" + (f" {u}" if u else "")
    if isinstance(value, list) and len(value) == 2 and all(_is_number(v) for v in value):
        a, b = number(value[0]), number(value[1])
        return f"{key} {a} {u.split()[0]} to {b} {u}" if u else f"{key} {a} to {b}"
    return None


def measured_text(measured: dict) -> str:
    parts = []
    for key, value in measured.items():
        if key in SKIPPED_KEYS:
            continue
        text = value_text(key, value)
        if text is None and isinstance(value, dict):
            inner = [value_text(f"{key}.{k}", v) for k, v in value.items() if not isinstance(v, (dict, list))]
            text = ", ".join(t for t in inner if t) or None
        if text:
            parts.append(text)
    return ", ".join(parts)


def gains_text(found) -> str:
    if found == "unrecorded" or found is None:
        return "unrecorded"
    return "; ".join(f"{g.get('file')} {g.get('key')} = {json.dumps(g.get('value'))}" for g in found)


def case_values_text(measured: dict) -> str:
    parts = []
    if "calibrationDecel" in measured:
        c = measured["calibrationDecel"]
        if c is None:
            parts.append("calibrationDecel unrecorded")
        elif "error" in c:
            parts.append(f"calibrationDecel unreadable ({c.get('file')}: {c['error']})")
        else:
            parts.append(f"calibrationDecel worstRatio {json.dumps(c.get('worstRatio'))}, "
                         f"allFollowWithinProposal {json.dumps(c.get('allFollowWithinProposal'))} ({c.get('file')})")
    if "ackermannGains" in measured:
        g = measured["ackermannGains"] or {}
        parts.append(f"ackermannGains requested {gains_text(g.get('requested'))}, "
                     f"readBack {gains_text(g.get('readBack'))}")
    desk = measured.get("desk")
    if isinstance(desk, dict):
        parts.append("desk reproduction valuesMatch " + number(desk["valuesMatch"])
                     if isinstance(desk.get("valuesMatch"), bool) else "desk reproduction without valuesMatch")
    return "; ".join(parts)


def run_usage(model: Model, info: RunInfo, rec: dict, identity: str, session: str) -> list[str]:
    attrs = rec["attributes"]
    if info.kind == "stop":
        what = (f"run {info.identity}, the further run of SC-DRIVING-012 in which the Eclipse S-CORE path of "
                "the driver-assistance system is stopped, which is no run of a setting, so setting is left "
                "empty as the record's rule says")
    else:
        what = (f"run {info.identity}, the {ORDINALS[int(info.repetition or 0)].lower()} run of the setting "
                f"{SETTING_LITERALS[str(info.setting)]}")
    text = f"{identity}. The evidence record of {what}, in the S1 session {session}; records.json names it run {info.label}."
    empty = rec["emptyAttributes"]
    if empty:
        missing = {m.split(": ", 1)[0]: m for m in rec.get("missing") or []}
        named = "; ".join(missing.get(a, f"{a}: no text in records.json") for a in empty)
        text += (" The record is partial, so every case that reads the run gives inconclusive, never pass. "
                 f"Its empty attributes, each left unbound, with the record and the field it was read from: "
                 f"{named}.")
    else:
        text += " The record is complete."
    lines = [f"  item {info.name} : {RUN_DEF} {{"] + doc_block([text], 4)
    for name, _type in model.run_attributes:
        value = attrs[name]
        if value is None:
            lines.append(f"    attribute :>> {name};")
        elif name == "scenario":
            lines.append(f"    attribute :>> scenario = {SCENARIO_ENUM}::{SCENARIO_LITERALS[value]};")
        elif name == "setting":
            lines.append(f"    attribute :>> setting = {SETTING_ENUM}::{SETTING_LITERALS[value]};")
        else:
            lines.append(f"    attribute :>> {name} = {sysml_string(value)};")
    return lines + ["  }"]


def analysis_empty(model: Model, analysis: dict) -> list[str]:
    return [a for a, _ in model.analysis_attributes
            if not (isinstance(analysis.get(a), str) and analysis[a].strip())]


def analysis_usage(model: Model, analysis: dict, identity: str) -> list[str]:
    empty = analysis_empty(model, analysis)
    text = f"{identity}. The record of the desk analysis of REQ-DRIVING-039, written from analysis_039.json."
    if empty:
        text += (" The record is partial, so the case gives inconclusive, never pass. Its empty attributes, "
                 f"each left unbound: {', '.join(empty)} (no value in analysis_039.json).")
    else:
        text += " The record is complete."
    lines = [f"  item {ANALYSIS_NAME} : {ANALYSIS_DEF} {{"] + doc_block([text], 4)
    for name, _type in model.analysis_attributes:
        if name in empty:
            lines.append(f"    attribute :>> {name};")
        else:
            lines.append(f"    attribute :>> {name} = {sysml_string(analysis[name])};")
    return lines + ["  }"]


def case_status(model: Model, vc: str, case: dict, verdicts: dict, infos: dict, identities: dict) -> str:
    measured = case.get("measured") or {}
    text = (f"{STATUS_START}{case['outcome']}; verdict: {case['verdict']}. Judged from the S1 session "
            f"{verdicts['sessionId']} by the case evaluators, with criteriaRecordIdentity "
            f"{case['criteriaRecordIdentity']} and evaluatorRevision {case['evaluatorRevision']}.")

    def entry(e: dict) -> str:
        info = infos[e["run"]]
        values = measured_text(e.get("measured") or {})
        return (f"{info.identity}, record {info.name} ({identities[info.name]}), {e['outcome']}"
                + (f": {values}" if values else ""))

    runs = [entry(e) for e in measured.get("runs") or []]
    stop = measured.get("stopClause")
    text += (" Runs read, each by its run identity with the record it reads, its outcome and the values "
             "measured: " + ("; ".join(runs) if runs else "none"))
    if isinstance(stop, dict) and stop.get("run"):
        text += f"; and, for the stop clause, {entry(stop)}"
    text += "."
    values = case_values_text(measured)
    if values:
        text += f" Values of the case: {values}."
    if case["verdict"] in ("inconclusive", "error"):
        reasons = list(dict.fromkeys(case.get("missing") or []))
        text += " Reason: " + ("; ".join(reasons) if reasons else "no run was judged") + "."
    return text


def analysis_status(model: Model, analysis: dict, identity: str) -> str:
    outcome = analysis["outcome"]
    reasons = [analysis["reason"]] if isinstance(analysis.get("reason"), str) and analysis["reason"] else []
    empty = analysis_empty(model, analysis)
    if empty:
        reasons.append(f"the analysis record is partial, empty: {', '.join(empty)}")
        if model.verdict(outcome) == "pass":
            outcome = INCONCLUSIVE
    verdict = model.verdict(outcome)
    text = (f"{STATUS_START}{outcome}; verdict: {verdict}. From the desk analysis, record {ANALYSIS_NAME} "
            f"({identity}), written from analysis_039.json; the case reads no run.")
    if verdict in ("inconclusive", "error") and reasons:
        text += " Reason: " + "; ".join(reasons) + "."
    return text


def patch_case_doc(text: str, vc: str, status: str) -> str:
    masked = code_mask(text)
    start, end = _block(text, masked, rf"verification <'{vc}'> \w+ : \w+ \{{")
    block = text[start:end]
    m = re.search(r"\n( *)doc /\*(.*?)\*/", block, re.S)
    if not m:
        raise InputError(f"{vc}: the case usage has no doc")
    paras = doc_paragraphs(m.group(2))
    if paras and paras[0].startswith(NOT_STARTED + " "):
        rest = [paras[0][len(NOT_STARTED) + 1:]] + paras[1:]
    elif paras and paras[0].startswith(STATUS_START):
        rest = paras[1:]
    else:
        raise InputError(f"{vc}: the doc starts neither with {NOT_STARTED!r} nor with a status")
    new_doc = "\n".join(doc_block([status] + rest, len(m.group(1))))
    block = block[:m.start() + 1] + new_doc + block[m.end():]
    return text[:start] + block + text[end:]


# ---------------------------------------------------------------- the whole
def generate(model_text: str, verdicts: dict, records: dict, analysis: dict | None, repo: Path = REPO,
             model_path: Path | None = None) -> Result:
    model = read_model(model_text)
    infos = validate(model, verdicts, records, analysis)
    kept = existing_identities(model_text)
    base = remove_generated(model_text)
    names = [i.name for i in infos] + ([ANALYSIS_NAME] if analysis is not None else [])
    identities, report = allocate(names, kept, scan_identities(Path(repo), model_path))
    blocks = [run_usage(model, i, records["records"][i.label], identities[i.name], verdicts["sessionId"])
              for i in infos]
    if analysis is not None:
        blocks.append(analysis_usage(model, analysis, identities[ANALYSIS_NAME]))
    header = "\n".join(_header_block())
    inserted = header + "\n" + "\n\n".join("\n".join(b) for b in blocks) + "\n\n"
    at = insertion_point(base)
    rest = base[at:]
    if not rest.startswith("\n\n"):
        raise InputError(f"no blank line after item def {ANALYSIS_DEF}")
    text = base[:at] + "\n\n" + inserted + rest[2:]
    by_label = {i.label: i for i in infos}
    for vc in CASES:
        if vc == ANALYSIS_CASE:
            if analysis is not None:
                text = patch_case_doc(text, vc, analysis_status(model, analysis, identities[ANALYSIS_NAME]))
            continue
        text = patch_case_doc(text, vc, case_status(model, vc, verdicts["cases"][vc], verdicts, by_label,
                                                    identities))
    if code_tokens(remove_generated(text)) != code_tokens(base):
        raise InputError("internal: the code outside the record usages changed")
    return Result(text, identities, report)


def _header_block() -> list[str]:
    lines = textwrap.wrap(HEADER, width=DOC_WIDTH - 5, break_on_hyphens=False, break_long_words=False)
    out = ["  /* " + lines[0]] + ["   * " + line for line in lines[1:]]
    out[-1] += " */"
    return out


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--verdicts", type=Path, required=True)
    ap.add_argument("--records", type=Path, required=True)
    ap.add_argument("--analysis-039", type=Path, default=None)
    ap.add_argument("--model", type=Path, default=MODEL)
    ap.add_argument("--repo", type=Path, default=REPO)
    ap.add_argument("--check", action="store_true", help="exit 1 when the model is not what the inputs give")
    a = ap.parse_args(argv)
    old = a.model.read_text(encoding="utf-8")
    try:
        result = generate(old, load(a.verdicts), load(a.records),
                          load(a.analysis_039) if a.analysis_039 else None, repo=a.repo, model_path=a.model)
    except InputError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 3
    print(result.allocation)
    for name, identity in result.identities.items():
        print(f"{identity} {name}")
    if a.check:
        if result.text != old:
            print(f"stale: {a.model} is not what the inputs give")
            return 1
        print(f"up to date: {a.model}")
        return 0
    if result.text != old:
        a.model.write_text(result.text, encoding="utf-8")
        print(f"wrote {a.model}")
    else:
        print(f"unchanged: {a.model}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
