"""The generator of the phase 10 evidence text of INC-DRIVING-002 (slice 10b).

`tools/generate_driver_assistance_evidence_text.py` reads the case evaluators'
`verdicts.json` and `records.json` (and optionally `analysis_039.json`) and
patches `driver_assistance_verification_evidence.sysml`: one item usage of
`RetainedAssistanceRunEvidence` per run, one of `RetainedCommandFormAnalysis`
when the desk analysis is given, and the status paragraph that replaces
"Not started." in the doc of each case usage VC-DRIVING-036 to -044.

The tests patch a temporary copy of the real package, read at test time; no
model file is copied into the repository. The fixtures under
`tests/fixtures/driver_assistance_evidence_text/` are the outputs of the case
evaluators (`evaluate_da_campaign.py` and `evidence_record.py`, branch
lane/da-s1-final at a9577eb5, run unchanged) on synthetic sessions written by
their `make_da_synthetic_run.py`, reduced to the keys the generator reads, with
long strings shortened:

- `complete.*.json`: the fourteen runs of the seven settings and the stop run,
  every record complete, every case pass (with the desk reproduction of 044);
- `partial.patch.json`: the same session with the chase view and the
  `candidate_rrd.json` of run 013_30_r2 removed: that record is partial and
  every case that reads the run is inconclusive;
- `fail.patch.json`: run 012_42_r1 gives no warning request: 042 fails;
- `rehearsal.*.json`: a session whose session.json says rehearsal true;
- `analysis_039.json`: a synthetic desk analysis of REQ-DRIVING-039.

A patch replaces the named records whole and, per case, the named keys and run
entries. No literal evidence identity appears in this file: the generator
greps `tests/` for them.
"""

from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tools import generate_driver_assistance_evidence_text as gen
from tools.sysml_html_viewer import model_parse

REPO = Path(__file__).resolve().parents[1]
MODEL = (REPO / "textual-notation-of-model" / "packages" / "features" / "driving"
         / "driver_assistance_verification_evidence.sysml")
FIX = Path(__file__).resolve().parent / "fixtures" / "driver_assistance_evidence_text"
TOOL = REPO / "tools" / "generate_driver_assistance_evidence_text.py"
RUN_DEF = "RetainedAssistanceRunEvidence"
ANALYSIS_DEF = "RetainedCommandFormAnalysis"
PREFIX = "EVID-" + "DRIVING-"
CASES = tuple(f"VC-DRIVING-{n:03d}" for n in range(36, 45))
RUN_CASES = tuple(vc for vc in CASES if vc != "VC-DRIVING-039")
# The model's literals for the evaluators' setting ids (the doc of enum def
# AssistanceSettingIdentity) and scenario ids (AssistanceScenarioIdentity).
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
ORDINALS = {1: "First", 2: "Second", 3: "Third", 4: "Fourth"}


# ---------------------------------------------------------------- fixtures
def _load(name: str) -> dict:
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def session(variant: str = "complete") -> tuple[dict, dict]:
    verdicts, records = _load("complete.verdicts.json"), _load("complete.records.json")
    if variant == "complete":
        return verdicts, records
    patch = _load(f"{variant}.patch.json")
    records["records"].update(patch["records"])
    for vc, change in patch["cases"].items():
        case = verdicts["cases"][vc]
        for key, value in change.items():
            if key == "runs":
                case["measured"]["runs"] = [value.get(e["run"], e) for e in case["measured"]["runs"]]
            elif key == "measuredOther":
                case["measured"].update(value)
            else:
                case[key] = value
    return verdicts, records


def analysis() -> dict:
    return _load("analysis_039.json")


# ---------------------------------------------------------------- independent text helpers
def _mask(text: str) -> str:
    """Comments, notes and strings blanked (newlines kept), quoted names kept."""
    out, i, n = list(text), 0, len(text)
    while i < n:
        if text.startswith("/*", i) or text.startswith("//", i):
            if text.startswith("/*", i) or text.startswith("//*", i):
                j = text.find("*/", i + 2)
                j = n if j < 0 else j + 2
            else:
                j = text.find("\n", i)
                j = n if j < 0 else j
            for p in range(i, j):
                if out[p] != "\n":
                    out[p] = " "
            i = j
        elif text[i] == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            for p in range(i + 1, min(j, n)):
                out[p] = "_"
            i = j + 1
        else:
            i += 1
    return "".join(out)


def _strip_comments(text: str) -> str:
    out, i, n = [], 0, len(text)
    while i < n:
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text[i] == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def _close(masked: str, opening: int) -> int:
    depth = 0
    for k in range(opening, len(masked)):
        if masked[k] == "{":
            depth += 1
        elif masked[k] == "}":
            depth -= 1
            if depth == 0:
                return k
    raise AssertionError("unbalanced braces")


def usages(text: str, definition: str) -> dict[str, str]:
    """Each package-level `item <name> : <definition> { ... }`, by name, raw text."""
    masked = _mask(text)
    found = {}
    for m in re.finditer(rf"^  item (\w+) : {definition} \{{", masked, re.M):
        found[m.group(1)] = text[m.start():_close(masked, m.end() - 1) + 1]
    return found


def _without_generated(text: str) -> str:
    masked = _mask(text)
    spans = []
    for m in re.finditer(rf"^  item \w+ : (?:{RUN_DEF}|{ANALYSIS_DEF}) \{{", masked, re.M):
        spans.append((m.start(), _close(masked, m.end() - 1) + 1))
    m = re.search(r"^  /\* Evidence records:.*?\*/\n", text, re.M | re.S)
    if m:
        spans.append((m.start(), m.end()))
    for start, end in sorted(spans, reverse=True):
        while end < len(text) and text[end] == "\n":
            end += 1
        text = text[:start] + text[end:]
    return text


def base_text() -> str:
    """The real package with any generated record usage removed."""
    text = _without_generated(MODEL.read_text(encoding="utf-8"))
    return re.sub(r"(\n  item def RetainedCommandFormAnalysis \{.*?\n  \})\n(?=  part def )", r"\1\n\n",
                  text, count=1, flags=re.S)


def usage(text: str, definition: str, name: str) -> str:
    found = usages(text, definition)
    assert name in found, f"no item usage {name} : {definition} in the patched package"
    return found[name]


def doc_of(block: str) -> str:
    m = re.search(r"doc /\*(.*?)\*/", block, re.S)
    assert m, block[:120]
    return m.group(1)


def doc_lines(block: str) -> list[str]:
    m = re.search(r"\n( *)doc /\*\n(.*?)\n *\*/", block, re.S)
    assert m, block[:120]
    return m.group(2).split("\n")


def paragraphs(doc: str) -> list[str]:
    paras, cur = [], []
    for line in doc.strip("\n").split("\n"):
        body = re.sub(r"^\s*\*\s?", "", line)
        if body.strip() == "":
            if cur:
                paras.append(" ".join(cur))
            cur = []
        else:
            cur.append(body.strip())
    if cur:
        paras.append(" ".join(cur))
    return [" ".join(p.split()) for p in paras]


def flat(doc: str) -> str:
    return " ".join(paragraphs(doc))


def case_block(text: str, vc: str) -> str:
    masked = _mask(text)
    m = re.search(rf"verification <'{vc}'> \w+ : \w+ \{{", masked)
    assert m, vc
    return text[m.start():_close(masked, m.end() - 1) + 1]


def model_attributes(definition: str) -> list[str]:
    code = _strip_comments(MODEL.read_text(encoding="utf-8"))
    m = re.search(rf"\bitem def {definition} \{{(.*?)\n  \}}", code, re.S)
    assert m, definition
    return re.findall(r"^\s*attribute (\w+) :", m.group(1), re.M)


def number(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(round(value, 3))
    return str(value)


def run_names(verdicts: dict) -> dict[str, str]:
    """The usage name of each run's record, by run label: the setting literal and the run's place."""
    names = {}
    for r in verdicts["runs"]:
        if r["kind"] == "stop":
            names[r["run"]] = "pathStoppedRunEvidence"
        else:
            names[r["run"]] = f"{SETTING_LITERALS[r['setting']]}{ORDINALS[r['repetition']]}RunEvidence"
    return names


def empty_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "textual-notation-of-model" / "packages").mkdir(parents=True, exist_ok=True)
    (repo / "tests").mkdir(exist_ok=True)
    return repo


def run_gen(tmp_path: Path, variant: str = "complete", with_analysis: bool = False, text: str | None = None,
            repo: Path | None = None):
    verdicts, records = session(variant)
    return gen.generate(text if text is not None else base_text(), verdicts, records,
                        analysis() if with_analysis else None, repo=repo or empty_repo(tmp_path))


# ---------------------------------------------------------------- the record usages
def test_one_record_usage_per_run_binds_every_attribute_of_the_model_in_order(tmp_path):
    verdicts, records = session()
    text = run_gen(tmp_path).text
    found = usages(text, RUN_DEF)
    names = run_names(verdicts)
    assert len(verdicts["runs"]) == 15
    assert sorted(found) == sorted(names.values())
    attributes = model_attributes(RUN_DEF)
    assert len(attributes) == 29
    for label, name in names.items():
        bound = re.findall(r"^    attribute :>> (\w+)\b", _strip_comments(found[name]), re.M)
        assert bound == attributes, name
        values = records["records"][label]["attributes"]
        for attribute in attributes:
            if attribute in ("scenario", "setting"):
                continue
            value = values[attribute]
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            assert f'    attribute :>> {attribute} = "{escaped}";' in found[name], (name, attribute)


def test_scenario_and_setting_bind_the_models_literals_and_the_stop_run_leaves_setting_empty(tmp_path):
    verdicts, records = session()
    found = usages(run_gen(tmp_path).text, RUN_DEF)
    assert sorted(found) == sorted(run_names(verdicts).values()), "one record usage per run"
    for label, name in run_names(verdicts).items():
        values = records["records"][label]["attributes"]
        scenario = SCENARIO_LITERALS[values["scenario"]]
        assert f"    attribute :>> scenario = AssistanceScenarioIdentity::{scenario};" in found[name]
        if values["setting"] is None:
            assert name == "pathStoppedRunEvidence"
            assert "    attribute :>> setting;" in found[name]
            assert "the further run" in flat(doc_of(found[name]))
            assert "setting is left empty" in flat(doc_of(found[name]))
        else:
            literal = SETTING_LITERALS[values["setting"]]
            assert f"    attribute :>> setting = AssistanceSettingIdentity::{literal};" in found[name]


def test_each_record_doc_starts_with_its_identity_and_names_the_run(tmp_path):
    verdicts, _ = session()
    result = run_gen(tmp_path)
    found = usages(result.text, RUN_DEF)
    assert sorted(found) == sorted(run_names(verdicts).values()), "one record usage per run"
    identities = []
    for r in verdicts["runs"]:
        name = run_names(verdicts)[r["run"]]
        text = flat(doc_of(found[name]))
        m = re.match(rf"({PREFIX}\d{{3}})\. ", text)
        assert m, text[:60]
        identities.append(m.group(1))
        assert r["runIdentity"] in text and f"run {r['run']}" in text and verdicts["sessionId"] in text
        assert "The record is complete." in text
    assert identities == [f"{PREFIX}{n:03d}" for n in range(1, 16)]
    assert result.identities == dict(zip([run_names(verdicts)[r["run"]] for r in verdicts["runs"]], identities))


def test_a_partial_record_names_every_empty_attribute_and_leaves_it_empty(tmp_path):
    verdicts, records = session("partial")
    rec = records["records"]["013_30_r2"]
    assert rec["outcome"] == "inconclusiveMissingEvidence"
    assert rec["emptyAttributes"] == ["rawObservationArtifact", "benchRecordingArtifact"]
    block = usage(run_gen(tmp_path, "partial").text, RUN_DEF, "slowerAt30SecondRunEvidence")
    text = flat(doc_of(block))
    assert "The record is partial" in text and "inconclusive, never pass" in text
    for attribute, missing in zip(rec["emptyAttributes"], rec["missing"]):
        assert missing.startswith(f"{attribute}: ")
        assert " ".join(missing.split()) in text
        assert f"    attribute :>> {attribute};" in block
        assert f"attribute :>> {attribute} =" not in block


def test_values_with_quotes_and_backslashes_are_escaped_as_sysml_strings(tmp_path):
    verdicts, records = session()
    records["records"]["012_20_r1"]["attributes"]["launchSettings"] = 'a "quoted" C:\\path'
    block = usage(gen.generate(base_text(), verdicts, records, None, repo=empty_repo(tmp_path)).text, RUN_DEF,
                  "stationaryAt20FirstRunEvidence")
    assert '    attribute :>> launchSettings = "a \\"quoted\\" C:\\\\path";' in block


# ---------------------------------------------------------------- identity allocation
def test_identities_start_the_sequence_when_packages_and_tests_hold_none(tmp_path):
    result = run_gen(tmp_path)
    assert result.allocation.startswith("no " + PREFIX + "NNN identity in textual-notation-of-model/ or tests/")
    assert f"{PREFIX}001" in result.allocation and f"{PREFIX}015" in result.allocation


def test_identities_continue_after_the_highest_one_found_in_the_packages_and_tests(tmp_path):
    repo = empty_repo(tmp_path)
    (repo / "textual-notation-of-model" / "packages" / "a.sysml").write_text(f"doc /* {PREFIX}004 */\n")
    (repo / "tests" / "test_a.py").write_text(f'assert "{PREFIX}007" not in raw\n')
    result = run_gen(tmp_path, repo=repo)
    assert len(result.identities) == 15, "one identity per run record"
    assert sorted(result.identities.values())[0] == f"{PREFIX}008"
    assert sorted(result.identities.values())[-1] == f"{PREFIX}022"
    assert "continues after " + PREFIX + "007" in result.allocation
    assert "tests/test_a.py" in result.allocation and "a.sysml" in result.allocation


def test_the_real_repository_scan_allocates_after_every_identity_it_holds(tmp_path):
    found = set()
    for root in ("textual-notation-of-model", "tests"):
        for path in (REPO / root).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                found |= {int(n) for n in re.findall(PREFIX + r"(\d{3})", path.read_text(errors="replace"))}
    model_text = MODEL.read_text(encoding="utf-8")
    held = {int(n) for n in re.findall(PREFIX + r"(\d{3})", model_text)}
    result = run_gen(tmp_path, text=model_text, repo=REPO)
    allocated = {int(v[-3:]) for v in result.identities.values()}
    new = allocated - held
    if not new:   # the real model already holds these records: their identities are kept
        assert allocated <= held
        return
    assert min(new) == max(found | {0}) + 1
    assert sorted(new) == list(range(min(new), min(new) + len(new)))


def test_a_second_generation_keeps_each_records_identity_by_its_name(tmp_path):
    held = empty_repo(tmp_path)
    (held / "tests" / "test_a.py").write_text(f'assert "{PREFIX}030" not in raw\n')
    first = run_gen(tmp_path, repo=held)
    assert len(first.identities) == 15, "one identity per run record"
    assert sorted(first.identities.values())[0] == f"{PREFIX}031"
    (held / "tests" / "test_a.py").unlink()   # the other holder is gone; the records keep theirs
    second = run_gen(tmp_path, "partial", with_analysis=True, text=first.text, repo=held)
    for name, identity in first.identities.items():
        assert second.identities[name] == identity
    assert second.identities["commandFormAnalysisEvidence"] == f"{PREFIX}046"
    assert "kept by name: 15" in second.allocation


# ---------------------------------------------------------------- the case paragraphs
def test_each_case_doc_starts_with_its_outcome_verdict_criteria_and_evaluator_revision(tmp_path):
    verdicts, _ = session()
    text = run_gen(tmp_path).text
    for vc in RUN_CASES:
        case = verdicts["cases"][vc]
        status = paragraphs(doc_of(case_block(text, vc)))[0]
        assert status.startswith(f"Outcome: {case['outcome']}; verdict: {case['verdict']}. "), vc
        assert f"criteriaRecordIdentity {case['criteriaRecordIdentity']}" in status
        assert f"evaluatorRevision {case['evaluatorRevision']}" in status
        assert verdicts["sessionId"] in status
        assert "Not started." not in flat(doc_of(case_block(text, vc)))


def test_each_case_names_every_run_it_reads_by_identity_with_its_record_and_outcome(tmp_path):
    verdicts, _ = session()
    result = run_gen(tmp_path)
    by_label = {r["run"]: r for r in verdicts["runs"]}
    names = run_names(verdicts)
    for vc in RUN_CASES:
        status = paragraphs(doc_of(case_block(result.text, vc)))[0]
        measured = verdicts["cases"][vc]["measured"]
        entries = measured["runs"] + ([measured["stopClause"]] if "stopClause" in measured else [])
        assert entries, vc
        for e in entries:
            name = names[e["run"]]
            assert name in result.identities, f"no record usage {name}"
            assert (f"{by_label[e['run']]['runIdentity']}, record {name} ({result.identities[name]}), "
                    f"{e['outcome']}") in status, (vc, e["run"])
        if "stopClause" in measured:
            assert "the stop clause" in status


def test_each_case_states_the_measured_values_with_their_units(tmp_path):
    verdicts, _ = session()
    text = run_gen(tmp_path).text
    status = {vc: paragraphs(doc_of(case_block(text, vc)))[0] for vc in RUN_CASES}
    # values of the complete fixture, read from verdicts.json by hand
    assert "approachKmh 21.0 km/h" in status["VC-DRIVING-037"]
    assert "impactKmh 0.0 km/h" in status["VC-DRIVING-037"]
    assert "limitKmh 0.0 km/h" in status["VC-DRIVING-037"]
    assert "functionalPart 605.0 s to 609.05 s of simulation time" in status["VC-DRIVING-036"]
    assert "leadS 2.2 s" in status["VC-DRIVING-042"]
    assert "firstWarningStartSimS 606.1 s of simulation time" in status["VC-DRIVING-042"]
    assert "recordBeforeFirstCommandNs 35000000 ns" in status["VC-DRIVING-044"]
    assert "diffBytes 111751 B" in status["VC-DRIVING-044"]
    assert "controlsAfterStop 0" in status["VC-DRIVING-038"]
    assert "stopSimS 2002.0 s of simulation time" in status["VC-DRIVING-043"]
    assert "valuesMatch true" in status["VC-DRIVING-044"]
    assert "calibrationDecel unrecorded" in status["VC-DRIVING-036"]
    assert "ackermannGains requested unrecorded, readBack unrecorded" in status["VC-DRIVING-037"]
    for vc in RUN_CASES:   # every number of every run entry, by its key
        m = verdicts["cases"][vc]["measured"]
        for e in m["runs"] + ([m["stopClause"]] if "stopClause" in m else []):
            for key, value in e["measured"].items():
                if isinstance(value, (bool, int, float)):
                    assert f"{key} {number(value)}" in status[vc], (vc, e["run"], key)


def test_the_rest_of_each_case_doc_is_kept_after_the_status(tmp_path):
    base = base_text()
    text = run_gen(tmp_path).text
    for vc in RUN_CASES:
        old = paragraphs(doc_of(case_block(base, vc)))
        description = " ".join(old)
        if description.startswith("Not started. "):
            description = description[len("Not started. "):]
        else:
            description = " ".join(old[1:])
        assert " ".join(paragraphs(doc_of(case_block(text, vc)))[1:]) == description, vc


def test_an_inconclusive_case_states_its_reason(tmp_path):
    verdicts, _ = session("partial")
    text = run_gen(tmp_path, "partial").text
    for vc in RUN_CASES:
        case = verdicts["cases"][vc]
        assert case["outcome"] == "inconclusiveMissingEvidence"
        status = paragraphs(doc_of(case_block(text, vc)))[0]
        assert status.startswith("Outcome: inconclusiveMissingEvidence; verdict: inconclusive. ")
        assert "Reason: " in status
        for missing in case["missing"]:
            assert " ".join(missing.split()) in status, vc
        assert "slowerAt30SecondRunEvidence" in status


def test_a_failed_case_states_the_failed_run(tmp_path):
    verdicts, _ = session("fail")
    text = run_gen(tmp_path, "fail").text
    status = paragraphs(doc_of(case_block(text, "VC-DRIVING-042")))[0]
    assert status.startswith("Outcome: failObservedBehavior; verdict: fail. ")
    assert "SC-DRIVING-012@42/r1, record stationaryAt42FirstRunEvidence" in status
    assert "failObservedBehavior: imminent true" in status
    assert "warningStarts 0" in status
    assert "Reason: " not in status


# ---------------------------------------------------------------- VC-DRIVING-039
def test_without_the_analysis_039_keeps_its_doc_and_gets_no_record(tmp_path):
    base = base_text()
    text = run_gen(tmp_path).text
    assert case_block(text, "VC-DRIVING-039") == case_block(base, "VC-DRIVING-039")
    assert usages(text, ANALYSIS_DEF) == {}


def test_the_analysis_record_binds_its_six_attributes_and_039_states_its_status(tmp_path):
    result = run_gen(tmp_path, with_analysis=True)
    block = usage(result.text, ANALYSIS_DEF, "commandFormAnalysisEvidence")
    attributes = model_attributes(ANALYSIS_DEF)
    assert len(attributes) == 6
    assert re.findall(r"^    attribute :>> (\w+)\b", _strip_comments(block), re.M) == attributes
    for attribute in attributes:
        assert f'    attribute :>> {attribute} = "{analysis()[attribute]}";' in block
    identity = result.identities["commandFormAnalysisEvidence"]
    assert identity == f"{PREFIX}016"
    assert flat(doc_of(block)).startswith(f"{identity}. ")
    assert "The record is complete." in flat(doc_of(block))
    status = paragraphs(doc_of(case_block(result.text, "VC-DRIVING-039")))[0]
    assert status.startswith("Outcome: passBoundedVerification; verdict: pass. ")
    assert f"record commandFormAnalysisEvidence ({identity})" in status
    assert "reads no run" in status


def test_a_partial_analysis_record_never_gives_pass(tmp_path):
    verdicts, records = session()
    partial = dict(analysis(), analystIdentity="")
    result = gen.generate(base_text(), verdicts, records, partial, repo=empty_repo(tmp_path))
    block = usage(result.text, ANALYSIS_DEF, "commandFormAnalysisEvidence")
    assert "    attribute :>> analystIdentity;" in block
    assert "analystIdentity" in flat(doc_of(block)) and "The record is partial" in flat(doc_of(block))
    status = paragraphs(doc_of(case_block(result.text, "VC-DRIVING-039")))[0]
    assert status.startswith("Outcome: inconclusiveMissingEvidence; verdict: inconclusive. ")
    assert "Reason: " in status and "analystIdentity" in status


def test_the_analysis_record_refuses_unknown_keys_and_outcomes(tmp_path):
    verdicts, records = session()
    for bad in (dict(analysis(), extra="x"), dict(analysis(), outcome="passed")):
        with pytest.raises(gen.InputError):
            gen.generate(base_text(), verdicts, records, bad, repo=empty_repo(tmp_path))


# ---------------------------------------------------------------- the text as a whole
def test_a_second_run_changes_nothing(tmp_path):
    repo = empty_repo(tmp_path)
    for variant in ("complete", "partial", "fail"):
        once = run_gen(tmp_path, variant, with_analysis=True, repo=repo).text
        assert len(usages(once, RUN_DEF)) == 15, "the first run wrote the records"
        assert run_gen(tmp_path, variant, with_analysis=True, text=once, repo=repo).text == once, variant


def test_regenerating_from_other_records_equals_generating_once(tmp_path):
    repo = empty_repo(tmp_path)
    partial = run_gen(tmp_path, "partial", with_analysis=True, repo=repo).text
    assert len(usages(partial, RUN_DEF)) == 15, "the first run wrote the records"
    assert (run_gen(tmp_path, "complete", with_analysis=True, text=partial, repo=repo).text
            == run_gen(tmp_path, "complete", with_analysis=True, repo=repo).text)


def test_generated_docs_wrap_at_80_columns_and_never_split_an_identifier(tmp_path):
    for variant in ("complete", "partial", "fail"):
        text = run_gen(tmp_path, variant, with_analysis=True).text
        blocks = list(usages(text, RUN_DEF).values()) + list(usages(text, ANALYSIS_DEF).values())
        assert len(blocks) == 16, "the records were written"
        blocks += [case_block(text, vc) for vc in CASES]
        for block in blocks:
            for line in doc_lines(block):
                assert re.match(r"^     \*( |$)", line), line
                assert not line.endswith("-"), line
                assert len(line) <= 80 or " " not in line[7:], line
        comment_lines = re.findall(r"^ *\*.*$", text, re.M)
        assert not [line for line in comment_lines if line.rstrip().endswith("-")]


def test_only_the_case_docs_change_and_the_record_usages_are_added(tmp_path):
    base = base_text()
    for variant in ("complete", "partial"):
        text = run_gen(tmp_path, variant, with_analysis=True).text
        restored = _without_generated(text)
        for vc in CASES:
            restored = restored.replace(case_block(restored, vc), case_block(base, vc))
        restored = re.sub(r"(\n  item def RetainedCommandFormAnalysis \{.*?\n  \})\n(?=  part def )", r"\1\n\n",
                          restored, count=1, flags=re.S)
        assert restored == base, variant
        # the comment-stripped code: the base's, plus the added usages
        assert (_strip_comments(_without_generated(text)).split() == _strip_comments(base).split())
        added = len(usages(text, RUN_DEF)) + len(usages(text, ANALYSIS_DEF))
        assert added == 16


def test_the_patched_package_parses_structurally(tmp_path):
    text = run_gen(tmp_path, "partial", with_analysis=True).text
    masked = _mask(text)
    depth = 0
    for ch in masked:
        depth += {"{": 1, "}": -1}.get(ch, 0)
        assert depth >= 0
    assert depth == 0
    assert masked.count("(") == masked.count(")") and masked.count("[") == masked.count("]")
    for block in list(usages(text, RUN_DEF).values()) + list(usages(text, ANALYSIS_DEF).values()):
        code = [line.rstrip() for line in _strip_comments(block).split("\n") if line.strip()]
        assert re.fullmatch(r"  item \w+ : \w+ \{", code[0]) and code[-1] == "  }"
        assert code[1] == "    doc"
        for line in code[2:-1]:
            assert re.fullmatch(r'    attribute :>> \w+(?: = (?:"(?:[^"\\]|\\.)*"|'
                                r"Assistance(?:Scenario|Setting)Identity::\w+))?;", line), line
    for enum, literal in re.findall(r"(Assistance(?:Scenario|Setting)Identity)::(\w+);", text):
        body = re.search(rf"enum def {enum} \{{(.*?)\}}", _strip_comments(text), re.S).group(1)
        assert re.search(rf"^\s*{literal};", body, re.M), literal
    path = tmp_path / "pkg" / MODEL.name
    path.parent.mkdir()
    path.write_text(text, encoding="utf-8")
    members = model_parse.parse_file(path, tmp_path).members
    items = {m.name: m for m in members if m.kind == "item"}
    names = set(run_names(session("partial")[0]).values()) | {"commandFormAnalysisEvidence"}
    assert names <= set(items)
    for name in names:
        assert items[name].type_name in (RUN_DEF, ANALYSIS_DEF)
        assert items[name].doc.strip().lstrip("* ").startswith(PREFIX)
    assert {m.name for m in members if m.kind == "verification" and m.short_name in CASES} == {
        m.name for m in model_parse.parse_file(MODEL, REPO).members
        if m.kind == "verification" and m.short_name in CASES}


def test_the_record_usage_names_are_declared_nowhere_else_in_the_model():
    names = set(run_names(session()[0]).values()) | {"commandFormAnalysisEvidence"}
    for root in ("textual-notation-of-model", "model-based-product-line-engineering"):
        for path in (REPO / root).rglob("*.sysml"):
            code = _without_generated(path.read_text(encoding="utf-8")) if path == MODEL else path.read_text(
                encoding="utf-8")
            for name in names:
                assert not re.search(rf"\b{name}\b", _strip_comments(code)), (path, name)


# ---------------------------------------------------------------- refusals
def test_a_rehearsal_session_is_refused_and_nothing_is_written(tmp_path):
    verdicts, records = _load("rehearsal.verdicts.json"), _load("rehearsal.records.json")
    with pytest.raises(gen.InputError, match="rehearsal"):
        gen.generate(base_text(), verdicts, records, None, repo=empty_repo(tmp_path))
    with pytest.raises(gen.InputError, match="rehearsal"):
        gen.generate(base_text(), session()[0], records, None, repo=empty_repo(tmp_path))


@pytest.mark.parametrize("breakage", ["session", "criteria", "verdict", "pass-on-partial", "run-set",
                                      "attribute-set", "setting", "evidence-records"])
def test_inconsistent_inputs_are_refused(tmp_path, breakage):
    verdicts, records = session("partial")
    if breakage == "session":
        records["sessionId"] = "another"
    elif breakage == "criteria":
        verdicts["cases"]["VC-DRIVING-036"]["criteriaRecordIdentity"] = "sha256:other"
    elif breakage == "verdict":
        verdicts["cases"]["VC-DRIVING-036"]["verdict"] = "pass"
    elif breakage == "pass-on-partial":
        verdicts["cases"]["VC-DRIVING-040"].update(outcome="passBoundedVerification", verdict="pass")
    elif breakage == "run-set":
        del records["records"]["stop"]
    elif breakage == "attribute-set":
        del records["records"]["stop"]["attributes"]["claimBoundary"]
    elif breakage == "setting":
        records["records"]["012_20_r1"]["attributes"]["setting"] = "SC-DRIVING-012@99"
    elif breakage == "evidence-records":
        verdicts["evidenceRecords"] = copy.deepcopy(records["records"])
        verdicts["evidenceRecords"]["stop"]["outcome"] = "complete?"
    with pytest.raises(gen.InputError):
        gen.generate(base_text(), verdicts, records, None, repo=empty_repo(tmp_path))


def test_a_doc_text_that_would_close_the_comment_is_refused(tmp_path):
    verdicts, records = session("partial")
    records["records"]["013_30_r2"]["missing"][0] += " */"
    with pytest.raises(gen.InputError, match=r"\*/"):
        gen.generate(base_text(), verdicts, records, None, repo=empty_repo(tmp_path))


# ---------------------------------------------------------------- the command line
def test_the_command_line_patches_the_file_and_check_reports_a_stale_file(tmp_path):
    verdicts, records = session()
    v, r, model = tmp_path / "verdicts.json", tmp_path / "records.json", tmp_path / MODEL.name
    v.write_text(json.dumps(verdicts))
    r.write_text(json.dumps(records))
    model.write_text(base_text(), encoding="utf-8")
    repo = empty_repo(tmp_path)
    cmd = [sys.executable, "-B", str(TOOL), "--verdicts", str(v), "--records", str(r), "--model", str(model),
           "--repo", str(repo)]
    before = model.read_bytes()
    check = subprocess.run(cmd + ["--check"], capture_output=True, text=True, cwd=REPO)
    assert check.returncode == 1, check.stdout + check.stderr
    assert model.read_bytes() == before
    write = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    assert write.returncode == 0, write.stdout + write.stderr
    assert "no " + PREFIX + "NNN identity" in write.stdout
    assert len(usages(model.read_text(encoding="utf-8"), RUN_DEF)) == 15
    again = subprocess.run(cmd + ["--check"], capture_output=True, text=True, cwd=REPO)
    assert again.returncode == 0, again.stdout + again.stderr
    refused = subprocess.run(cmd[:4] + [str(FIX / "rehearsal.verdicts.json")] + cmd[5:], capture_output=True,
                             text=True, cwd=REPO)
    assert refused.returncode == 3 and "rehearsal" in refused.stderr
