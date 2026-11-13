"""The gap claim, tested in both directions.

* a case that needs a record becomes inconclusiveMissingEvidence - never a
  pass - when that record is removed from a copy of its run;
* a case with no `needs` still passes with every record change removed;
* the change list of gaps.py agrees with what the evaluators declare, and so
  does the status table and the "Against ICD v2" section of OBSERVABLES.md.
"""

from __future__ import annotations

import pytest

import cases
import gaps
import strip
from conftest import CASE_RUN, verdict

MISSING = set(gaps.V2_GAPS)
WITH_NEEDS = sorted(vc for vc, s in cases.CASES.items() if s["needs"])
NO_NEEDS = sorted(vc for vc, s in cases.CASES.items() if not s["needs"])


def test_change_list_agrees_with_the_evaluators():
    """ICD_CHANGES.unblocks must be exactly what CASES[vc].needs says."""
    derived: dict[str, list[str]] = {cid: [] for cid in gaps.ICD_CHANGES}
    for vc, spec in cases.CASES.items():
        for cid in spec["needs"]:
            assert cid in gaps.ICD_CHANGES, f"{vc} needs unknown change {cid}"
            derived[cid].append(vc)
    for cid, declared in gaps.ICD_CHANGES.items():
        assert sorted(declared["unblocks"]) == sorted(derived[cid]), cid


def test_every_change_has_a_strip_rule():
    assert set(gaps.ICD_CHANGES) == set(strip.RULES)


@pytest.mark.parametrize("vc", WITH_NEEDS)
def test_a_needed_record_cannot_be_stripped_and_still_pass(vc, run_for, tmp_path):
    needs = cases.CASES[vc]["needs"]
    first = needs[0]
    stripped = strip.strip_change(run_for(CASE_RUN[vc]).root, first, tmp_path / vc)
    from runio import Run
    res = verdict(Run(stripped), vc)
    assert res.outcome == cases.INCONCL, (vc, first, res.outcome, res.measured)
    assert res.missing, vc
    assert first in res.icd_changes, (vc, res.icd_changes)


@pytest.mark.parametrize("vc", NO_NEEDS)
def test_cases_without_needs_survive_every_strip(vc, run_for, tmp_path):
    stripped = strip.strip_changes(run_for(CASE_RUN[vc]).root,
                                   sorted(strip.RULES), tmp_path / vc)
    from runio import Run
    res = verdict(Run(stripped), vc)
    assert res.outcome == cases.PASS, (vc, res.outcome, res.missing, res.notes)


def _md_rows():
    import re
    from pathlib import Path
    text = (Path(__file__).resolve().parent.parent / "OBSERVABLES.md").read_text()
    head = text.split("## 2.")[0]          # the case table only
    rows = {}
    for line in head.splitlines():
        if not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not re.fullmatch(r"\d{3}", cells[0]):
            continue
        rows[f"VC-DRIVING-{cells[0]}"] = cells[-1]
    return text, rows


def test_observables_table_matches_the_evaluators():
    """The status column must say SUPPORTED/MISSING exactly as gaps.V2_GAPS does."""
    text, rows = _md_rows()
    assert len(rows) == 35
    assert set(rows) == set(cases.CASES) | {"VC-DRIVING-018", "VC-DRIVING-019"}
    for vc, status in rows.items():
        if vc in MISSING:
            assert "MISSING" in status, (vc, status)
            for cid in cases.CASES[vc]["needs"]:
                assert cid in status, (vc, cid, status)
        else:
            assert "SUPPORTED" in status and "MISSING" not in status, (vc, status)


def test_against_icd_v2_section_lists_every_gap():
    text, _ = _md_rows()
    assert "## 2. Against ICD v2" in text
    section = text.split("## 2. Against ICD v2", 1)[1].split("## 3.", 1)[0]
    for vc in gaps.V2_GAPS:
        assert vc in section, vc
    assert "SUPPORTED" in section and "MISSING" in section
