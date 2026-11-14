"""The DRIVING identity series is shared by the increments of the driving folder.

The tests of one increment read the packages that its charter names. What they cannot see is a short name of the
series that another increment declares a second time. This check reads every model file for it.
"""

from __future__ import annotations

from pathlib import Path

from sysml_shapes import short_name_declarations

ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOTS = (ROOT / "textual-notation-of-model", ROOT / "model-based-product-line-engineering")


def test_each_short_name_of_the_driving_series_is_declared_once_in_the_model():
    declared = short_name_declarations(r"[A-Z]+-DRIVING-[A-Z0-9-]+", MODEL_ROOTS)
    assert len(declared) >= 100, "the population of the check must not be vacuous"
    for kind in ("INC", "NEED", "REQ", "VC", "GAP"):
        assert any(short.startswith(f"{kind}-DRIVING-") for short in declared), kind
    more_than_once = {short: [path.name for path in paths] for short, paths in declared.items() if len(paths) != 1}
    assert not more_than_once, f"a short name of the series is never used a second time: {more_than_once}"
