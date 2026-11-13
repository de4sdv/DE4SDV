"""The one change of the evaluators' output: each case names the requirement it verifies.

cases.py gives each registered case the requirement the catalogue names for it (``CASES[vc]["requirement"]``),
and every case object the evaluators write, in verdicts.json and in campaign_verdicts.json, carries it right
after "vc". This step is kept apart: dropping it is dropping this file and the lines of cases.py and
evaluate_run.py that name "requirement".
"""

from __future__ import annotations

import json
from pathlib import Path

import cases
import evaluate_campaign
import evaluate_run

CATALOGUE = Path(__file__).resolve().parent.parent / "driving_case_catalogue.json"


def _requirements() -> dict[str, str]:
    return {case["id"]: case["requirement"]
            for case in json.loads(CATALOGUE.read_text(encoding="utf-8"))["cases"]}


def test_each_registered_case_holds_the_catalogues_requirement():
    """Cannot see: whether the requirement is the one the evaluator's criteria come from (the model ties them)."""
    requirements = _requirements()
    assert cases.CASES and all("requirement" in spec for spec in cases.CASES.values())
    assert {vc: spec["requirement"] for vc, spec in cases.CASES.items()} == {vc: requirements[vc] for vc in cases.CASES}


def test_a_case_object_carries_the_requirement_right_after_vc():
    """For every case of the catalogue, the two campaign cases included.

    Cannot see: readers of verdicts.json that expect the earlier keys only (listed in the change's report).
    """
    requirements = _requirements()
    for vc in sorted(requirements):
        case = cases.Result(vc, cases.PASS).as_dict()
        assert list(case)[:3] == ["vc", "requirement", "outcome"], (vc, list(case))
        assert case["requirement"] == requirements[vc]


def test_the_verdict_files_carry_the_requirement(fixture_root, tmp_path):
    """The verdicts of the nominal run, of an unreadable run and of the fixture's campaigns.

    Cannot see: a reader that compares whole case objects of verdict files written before this change.
    """
    requirements = _requirements()
    unreadable = tmp_path / "unreadable"
    unreadable.mkdir()
    (unreadable / "run_record.json").write_text("{not json", encoding="utf-8")
    reports = [evaluate_run.evaluate(fixture_root / "nominal"), evaluate_run.evaluate(unreadable),
               evaluate_campaign.evaluate_campaign(fixture_root)]
    for report in reports:
        assert report["cases"]
        for vc, case in report["cases"].items():
            assert list(case)[:3] == ["vc", "requirement", "outcome"], (vc, list(case))
            assert case["requirement"] == requirements[vc], vc
