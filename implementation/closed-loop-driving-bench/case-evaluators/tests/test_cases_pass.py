"""Every evaluable case passes on the synthetic run of its own bench."""

from __future__ import annotations

import cases
import gaps
from conftest import CASE_RUN, verdict


CAMPAIGN_ONLY = {"VC-DRIVING-018", "VC-DRIVING-019"}
MISSING = set(gaps.V2_GAPS)


def test_every_case_has_a_run():
    assert set(cases.CASES) == set(CASE_RUN)
    assert CAMPAIGN_ONLY.isdisjoint(CASE_RUN)


def test_every_supported_case_passes_on_its_run(run_for):
    failures = []
    for vc, run_name in CASE_RUN.items():
        if vc in MISSING:
            continue
        res = verdict(run_for(run_name), vc)
        if res.outcome != cases.PASS:
            failures.append((vc, run_name, res.outcome, res.missing, res.notes))
    assert not failures, failures


def test_every_missing_case_is_inconclusive_and_names_its_gap(run_for):
    bad = []
    for vc, gap in gaps.V2_GAPS.items():
        res = verdict(run_for(CASE_RUN[vc]), vc)
        if res.outcome != cases.INCONCL or not res.missing:
            bad.append((vc, res.outcome, res.missing, res.notes))
    assert not bad, bad


def test_no_case_is_silently_skipped(run_for):
    """Each case evaluates to a country on its own run -- not 'not applicable'."""
    skipped = []
    for vc, run_name in CASE_RUN.items():
        res = verdict(run_for(run_name), vc)
        if res.outcome == cases.NOT_APPLICABLE:
            skipped.append((vc, run_name))
    assert not skipped, skipped
