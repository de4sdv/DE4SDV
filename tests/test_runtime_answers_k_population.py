"""The K pair's reviewed witness population (population review: PR #352).

Synthetic collected records only; no runtime, no API. Forward and inverse share one witness population,
and its size must equal the reviewed baseline; any other size is NOT_YET_COMPARABLE, never equivalence.
"""
from __future__ import annotations

import pytest

from de4sdv.semantic import runtime_answers as ra


def _collected(count):
    records = {f"s-{i}": {"witnesses": [f"w-{i}"]} for i in range(count)}
    return {predicate: {"records": dict(records)} for predicate in ra.K_PAIR}


def test_reviewed_population_is_27_and_equivalent():
    assert ra.READINESS_BASELINE_K_WITNESS_COUNT == 27
    result = ra.k_self_evidence(_collected(27))
    assert result["classification"] == "EQUIVALENT"
    assert result["population_complete"] is True


@pytest.mark.parametrize("count", [5, 26, 28])
def test_other_population_sizes_are_not_yet_comparable(count):
    result = ra.k_self_evidence(_collected(count))
    assert result["classification"] == "NOT_YET_COMPARABLE"
    assert f"witness population is {count}; the reviewed baseline is 27" in result["missing"][0]
