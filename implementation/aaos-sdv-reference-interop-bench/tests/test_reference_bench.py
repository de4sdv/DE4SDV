from pathlib import Path
import sys

import pytest

BENCH = Path(__file__).parents[1]
sys.path.insert(0, str(BENCH / "src"))
sys.path.insert(0, str(BENCH.parents[0] / "vss-vehicle-speed-adapter" / "src"))

from de4sdv_aaos_sdv_reference_bench import (  # noqa: E402
    IndependentObserver,
    ReferenceProvider,
    run_reference_rehearsal,
)


def test_reference_rehearsal_produces_independent_pass_evidence():
    evidence = run_reference_rehearsal(speed_kmh=72.0, timestamp_ns=42)

    assert evidence["claim"] == "de4sdv_reference_contract_rehearsal"
    assert evidence["passed"] is True
    assert evidence["output_longitudinal_velocity_mps"] == pytest.approx(20.0)
    assert evidence["observer"] == "IndependentObserver"
    assert evidence["aaos_runtime_interoperability"] == "not_proven"


def test_provider_emits_vss_sample():
    sample = ReferenceProvider(36.0, 99).sample()

    assert sample.semantic_path == "Vehicle.Speed"
    assert sample.unit == "km/h"
    assert sample.value == 36.0


def test_observer_rejects_missing_output():
    observer = IndependentObserver()

    with pytest.raises(AssertionError, match="expected one output"):
        observer.verify(expected_speed_kmh=36.0, expected_timestamp_ns=1)
