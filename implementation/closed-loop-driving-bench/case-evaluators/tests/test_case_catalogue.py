"""The case catalogue the evaluators take from the model.

driving_case_catalogue.json beside cases.py is written from the SysML model by the repository's
scripts/generate_driving_case_catalogue.py and is never edited by hand. cases.py reads it at import: the
outcomes and the verdict of each, the scenarios and the cases. These tests change copies of the file in a
temporary folder, call the import-time check directly, import a copy of the evaluators beside a changed
catalogue in a fresh interpreter, and read the verdicts the evaluators write.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import cases
import evaluate_campaign
import evaluate_run

EVALUATORS = Path(__file__).resolve().parent.parent
REAL = EVALUATORS / "driving_case_catalogue.json"
GENERATOR = ("python3 scripts/generate_driving_case_catalogue.py --output "
             "implementation/closed-loop-driving-bench/case-evaluators/driving_case_catalogue.json")
KEYS = ("schema", "generated_from", "outcomes", "verdicts", "verdict_otherwise", "scenarios", "cases")


def _real() -> dict:
    return json.loads(REAL.read_text(encoding="utf-8"))


def _write(folder: Path, data) -> Path:
    path = folder / "driving_case_catalogue.json"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _refused(path: Path, message: str) -> None:
    """load_catalogue refuses the file with ``message`` and names the generator command."""
    with pytest.raises(cases.CatalogueError, match=message) as refused:
        cases.load_catalogue(path)
    assert GENERATOR in str(refused.value)


# ---------------------------------------------------------------- the loader
def test_the_evaluators_hold_the_catalogue_beside_them():
    """cases.py loaded the file beside it, and its tables are the catalogue's.

    Cannot see: whether the file is the generator's output from the model of the checkout (the repository's
    check_repo.py compares them).
    """
    data = _real()
    assert cases.CATALOGUE_FILE == REAL
    assert cases.load_catalogue() == data == cases.CATALOGUE
    assert list(cases.OUTCOMES) == data["outcomes"]
    assert cases.VERDICT == data["verdicts"]
    assert cases.VERDICT_OTHERWISE == data["verdict_otherwise"]
    assert list(cases.SCENARIOS) == data["scenarios"]
    assert list(cases.CASE_IDS) == [case["id"] for case in data["cases"]]


def test_the_loader_refuses_a_missing_file(tmp_path):
    """Cannot see: a file of the right shape whose content is stale."""
    _refused(tmp_path / "driving_case_catalogue.json", "is missing")


@pytest.mark.parametrize("text", ["{not json", "[]", '{"schema": "a", "schema": "b"}'],
                         ids=["not-json", "not-an-object", "a-key-twice"])
def test_the_loader_refuses_a_file_it_cannot_read(tmp_path, text):
    """Cannot see: a readable file with the wrong numbers in it."""
    path = tmp_path / "driving_case_catalogue.json"
    path.write_text(text, encoding="utf-8")
    _refused(path, "cannot be read|is no JSON object|holds the key")


def test_the_loader_refuses_a_wrong_schema_name(tmp_path):
    """Cannot see: a v1 document written by another generator."""
    data = _real()
    data["schema"] = "de4sdv.driving.case-catalogue.v2"
    _refused(_write(tmp_path, data), "has the schema 'de4sdv.driving.case-catalogue.v2'")


@pytest.mark.parametrize("key", KEYS)
def test_the_loader_refuses_a_missing_key(tmp_path, key):
    """Cannot see: a key whose value has the right shape and the wrong content."""
    data = _real()
    del data[key]
    _refused(_write(tmp_path, data), f"lacks the key {key}")


def test_the_loader_refuses_an_outcome_without_a_verdict(tmp_path):
    """Cannot see: a verdict that is another one than the model's (the stale check of check_repo.py does)."""
    data = _real()
    del data["verdicts"]["blockedTargetRuntime"]
    _refused(_write(tmp_path, data), "gives no verdict for the outcome blockedTargetRuntime")


def test_the_loader_refuses_a_case_without_its_requirement_and_a_case_twice(tmp_path):
    """Cannot see: a requirement id that is well formed and wrong."""
    data = _real()
    del data["cases"][0]["requirement"]
    _refused(_write(tmp_path, data), "case 1 has the keys")
    data = _real()
    data["cases"].append(dict(data["cases"][0]))
    _refused(_write(tmp_path, data), "names the case VC-DRIVING-001 twice")


# ---------------------------------------------------------------- the import-time check
def test_the_import_check_passes_the_evaluators_as_they_are():
    """Positive control of the refusals below.

    Cannot see: the order of the cases, which the check does not read.
    """
    cases.check_registry(cases.CATALOGUE, cases.CASES, cases.CAMPAIGN_CASES, cases.SCENARIO_CASES)


def test_the_import_check_refuses_a_case_id_the_model_lacks():
    """An evaluator registered under a case id the catalogue does not hold stops the import, named by its id.

    Cannot see: an evaluator that judges another case than the one it is registered under.
    """
    registered = dict(cases.CASES)
    registered["VC-DRIVING-036"] = dict(cases.CASES["VC-DRIVING-001"])
    with pytest.raises(cases.CatalogueError, match="VC-DRIVING-036 has an evaluator but is no case of the model"):
        cases.check_registry(cases.CATALOGUE, registered, cases.CAMPAIGN_CASES, cases.SCENARIO_CASES)
    with pytest.raises(cases.CatalogueError, match="VC-DRIVING-018 is registered both"):
        cases.check_registry(cases.CATALOGUE, {**cases.CASES, "VC-DRIVING-018": dict(cases.CASES["VC-DRIVING-001"])},
                             cases.CAMPAIGN_CASES, cases.SCENARIO_CASES)


def test_the_import_check_refuses_a_case_of_the_model_without_an_evaluator():
    """A case of the catalogue with neither an @case nor a campaign evaluator stops the import, named by its id.

    Cannot see: whether evaluate_campaign.py judges the campaign cases it is credited with.
    """
    registered = {vc: spec for vc, spec in cases.CASES.items() if vc != "VC-DRIVING-001"}
    with pytest.raises(cases.CatalogueError, match="VC-DRIVING-001 of the model has no evaluator"):
        cases.check_registry(cases.CATALOGUE, registered, cases.CAMPAIGN_CASES, cases.SCENARIO_CASES)
    with pytest.raises(cases.CatalogueError, match="VC-DRIVING-019 of the model has no evaluator"):
        cases.check_registry(cases.CATALOGUE, cases.CASES, ("VC-DRIVING-018",), cases.SCENARIO_CASES)


def test_the_import_check_refuses_an_unknown_scenario():
    """A scenario name of a decorator or a key of SCENARIO_CASES that is no scenario of the catalogue stops the
    import, named.

    Cannot see: a scenario name used elsewhere in the evaluators (label_conflicts names checkpointRefusal).
    """
    registered = dict(cases.CASES)
    registered["VC-DRIVING-001"] = {**cases.CASES["VC-DRIVING-001"], "scenarios": ("closedLoopRide",)}
    with pytest.raises(cases.CatalogueError, match="'closedLoopRide' of the case VC-DRIVING-001"):
        cases.check_registry(cases.CATALOGUE, registered, cases.CAMPAIGN_CASES, cases.SCENARIO_CASES)
    with pytest.raises(cases.CatalogueError, match="SCENARIO_CASES names the scenario 'rainyRoute'"):
        cases.check_registry(cases.CATALOGUE, cases.CASES, cases.CAMPAIGN_CASES,
                             {**cases.SCENARIO_CASES, "rainyRoute": []})


def _import_beside(tmp_path: Path, change) -> subprocess.CompletedProcess:
    """Import a copy of the evaluators, in a fresh interpreter, beside a copy of the catalogue changed by ``change``."""
    copy = tmp_path / "case-evaluators"
    copy.mkdir()
    for source in EVALUATORS.glob("*.py"):
        shutil.copy2(source, copy / source.name)
    data = _real()
    change(data)
    _write(copy, data)
    environment = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, "-B", "-c", "import cases"], cwd=copy, env=environment,
                          capture_output=True, text=True, timeout=600)


def _unchanged(data):
    pass


def _without(vc):
    def change(data):
        data["cases"] = [case for case in data["cases"] if case["id"] != vc]
    return change


def _with_a_36th_case(data):
    data["cases"].append({"id": "VC-DRIVING-036", "usage": "extraVerification", "definition": "ExtraVerification",
                          "requirement": "REQ-DRIVING-036"})


def _scenario_renamed(data):
    data["scenarios"] = ["closedLoopRide" if s == "closedLoopRoute" else s for s in data["scenarios"]]


def _outcome_renamed(data):
    data["outcomes"] = ["errorRecord" if o == "errorEvidence" else o for o in data["outcomes"]]
    data["verdicts"] = {("errorRecord" if o == "errorEvidence" else o): v for o, v in data["verdicts"].items()}


@pytest.mark.parametrize("change, named", [
    (_unchanged, None),
    (_without("VC-DRIVING-035"), "VC-DRIVING-035"),
    (_without("VC-DRIVING-018"), "VC-DRIVING-018"),
    (_with_a_36th_case, "VC-DRIVING-036"),
    (_scenario_renamed, "closedLoopRoute"),
    (_outcome_renamed, "errorEvidence"),
], ids=["unchanged", "a-case-dropped", "a-campaign-case-dropped", "a-case-added", "a-scenario-renamed",
        "an-outcome-renamed"])
def test_the_evaluators_refuse_to_import_beside_a_catalogue_they_disagree_with(tmp_path, change, named):
    """The import-time checks as wired in cases.py: a copy of the evaluators imports beside the unchanged
    catalogue and stops with a CatalogueError naming the id, the scenario or the outcome beside a changed one.

    Cannot see: evaluate_run.py and evaluate_campaign.py, which import cases and stop with it.
    """
    result = _import_beside(tmp_path, change)
    if named is None:
        assert result.returncode == 0, result.stderr
        return
    assert result.returncode != 0
    last = result.stderr.strip().splitlines()[-1]
    assert last.startswith("cases.CatalogueError:") and named in last, result.stderr[-2000:]


# ---------------------------------------------------------------- the verdicts
def test_each_outcome_gives_the_catalogues_verdict_and_anything_else_the_else_branch():
    """Result.as_dict takes the verdict from the catalogue, and the else branch for a value that is no outcome.

    Cannot see: which outcome an evaluator chooses for a record.
    """
    data = _real()
    for outcome, verdict in data["verdicts"].items():
        assert cases.Result("VC-DRIVING-001", outcome).as_dict()["verdict"] == verdict, outcome
    assert cases.Result("VC-DRIVING-001", cases.NOT_APPLICABLE).as_dict()["verdict"] == data["verdict_otherwise"]


def test_the_summary_keys_are_the_verdict_vocabulary_in_todays_order(tmp_path):
    """The keys of a summary are the verdicts of the catalogue in the order of the outcomes that give them, with
    the else branch's last: today pass, fail, inconclusive, error, the order of the verdict files written so far.

    Cannot see: a model that reorders its outcomes, which would reorder the keys; this test then fails.
    """
    assert cases.VERDICTS == ("pass", "fail", "inconclusive", "error")
    assert list(evaluate_campaign.evaluate_campaign(tmp_path)["summary"]) == list(cases.VERDICTS)


def test_an_unreadable_run_errors_every_case_by_the_verdict_rule(tmp_path):
    """An unreadable run record: every case object has the verdict of errorEvidence, and the summary counts the
    catalogue's 35 cases as errors while the case objects are the 33 cases with a single-run evaluator. Those are
    the bytes the evaluators wrote before the catalogue, kept on purpose.

    Cannot see: why the summary counts the two campaign cases that the case objects leave out (an open question).
    """
    run = tmp_path / "unreadable"
    run.mkdir()
    (run / "run_record.json").write_text("{not json", encoding="utf-8")
    report = evaluate_run.evaluate(run)
    assert {case["verdict"] for case in report["cases"].values()} == {cases.VERDICT[cases.ERROR]} == {"error"}
    assert len(report["cases"]) == 33
    assert list(report["summary"].items()) == [("pass", 0), ("fail", 0), ("inconclusive", 0), ("error", 35)]
    assert report["summary"]["error"] == len(_real()["cases"])
