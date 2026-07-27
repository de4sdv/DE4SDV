from pathlib import Path

import pytest
import yaml

from scripts.aebs_regulatory_criteria import (
    evaluate_regulatory_measurement,
    maximum_impact_speed_kmh,
)

ROOT = Path(__file__).resolve().parents[1]
CRITERIA = ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-regulatory-criteria.yaml"


def _fit_measurement() -> dict:
    return {
        "scenario_family": "pedestrian",
        "vehicle_category": "M1",
        "load_condition": "mass_in_running_order",
        "subject_speed_kmh": 20.0,
        "target_speed_kmh": 5.0,
        "warning_time_s": 1.0,
        "braking_start_time_s": 1.1,
        "minimum_braking_demand_mps2": -5.0,
        "impact_speed_kmh": 0.0,
        "successful_repetitions": 2,
        "failed_repetitions": 0,
        "conditions": {
            "flat_dry_high_adhesion_surface": True,
            "pbc_at_least_0_9": True,
            "slope_between_0_and_1_percent": True,
            "temperature_between_0_and_45_c": True,
            "visibility_complete": True,
            "wind_not_result_affecting": True,
            "illumination_at_least_2000_lux": True,
            "prescribed_mass_controlled": True,
            "prescribed_soft_target_fidelity": True,
            "straight_approach_at_least_2_s": True,
            "functional_start_ttc_at_least_4_s": True,
            "impact_offset_within_0_1_m": True,
            "no_disallowed_driver_adjustment": True,
            "measurement_uncertainty_controlled": True,
        },
    }


def test_criteria_are_bound_to_the_controlled_source() -> None:
    value = yaml.safe_load(CRITERIA.read_text(encoding="utf-8"))
    assert value["schema"] == "de4sdv.aebs-regulatory-criteria.v1"
    assert value["source_id"] == "E/ECE/TRANS/505/Rev.3/Add.151/Rev.2"
    assert value["source_original_sha256"] == "dc9cc84498dcae8f0888067ad3967fb5a346e814bc2f19128987a654c8a193de"
    assert value["result_vocabulary"] == ["pass", "fail", "inconclusive"]


def test_next_higher_speed_row_applies_between_listed_values() -> None:
    assert maximum_impact_speed_kmh("pedestrian", "M1", "mass_in_running_order", 41.0) == 0.0
    assert maximum_impact_speed_kmh("pedestrian", "M1", "maximum_mass", 41.0) == 10.0
    assert maximum_impact_speed_kmh("bicycle", "N1", "maximum_mass", 37.0) == 15.0


def test_out_of_range_and_boolean_speed_fail_closed() -> None:
    with pytest.raises(ValueError):
        maximum_impact_speed_kmh("pedestrian", "M1", "maximum_mass", 19.9)
    with pytest.raises(TypeError):
        maximum_impact_speed_kmh("pedestrian", "M1", "maximum_mass", True)


def test_fit_measurement_meets_quantified_criteria_without_compliance_claim() -> None:
    result = evaluate_regulatory_measurement(_fit_measurement())
    assert result["threshold_result"] == "pass"
    assert result["evidence_fitness"] == "fit"
    assert result["criterion_result"] == "pass"
    assert result["compliance_conclusion"] == "withheld"
    assert result["maximum_impact_speed_kmh"] == 0.0


def test_favorable_numbers_remain_inconclusive_when_target_fidelity_is_missing() -> None:
    measurement = _fit_measurement()
    measurement["conditions"]["prescribed_soft_target_fidelity"] = False
    result = evaluate_regulatory_measurement(measurement)
    assert result["threshold_result"] == "pass"
    assert result["evidence_fitness"] == "inconclusive"
    assert result["criterion_result"] == "inconclusive"
    assert "prescribed_soft_target_fidelity" in result["unestablished_conditions"]


def test_threshold_failure_is_not_hidden_by_fit_evidence() -> None:
    measurement = _fit_measurement()
    measurement["impact_speed_kmh"] = 0.1
    result = evaluate_regulatory_measurement(measurement)
    assert result["threshold_result"] == "fail"
    assert result["evidence_fitness"] == "fit"
    assert result["criterion_result"] == "fail"


def test_two_successful_repetitions_are_required() -> None:
    measurement = _fit_measurement()
    measurement["successful_repetitions"] = 1
    result = evaluate_regulatory_measurement(measurement)
    assert result["criterion_result"] == "inconclusive"
    assert "successful_repetitions" in result["unestablished_conditions"]


def test_measurement_shape_is_closed() -> None:
    measurement = _fit_measurement()
    measurement["invented"] = "field"
    with pytest.raises(ValueError, match="measurement keys"):
        evaluate_regulatory_measurement(measurement)
