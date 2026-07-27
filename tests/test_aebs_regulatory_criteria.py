import unittest
from pathlib import Path

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


class TestAebsRegulatoryCriteria(unittest.TestCase):
    def test_criteria_are_bound_to_the_controlled_source(self) -> None:
        value = yaml.safe_load(CRITERIA.read_text(encoding="utf-8"))
        self.assertEqual(value["schema"], "de4sdv.aebs-regulatory-criteria.v1")
        self.assertEqual(value["source_id"], "E/ECE/TRANS/505/Rev.3/Add.151/Rev.2")
        self.assertEqual(
            value["source_original_sha256"],
            "dc9cc84498dcae8f0888067ad3967fb5a346e814bc2f19128987a654c8a193de",
        )
        self.assertEqual(value["result_vocabulary"], ["pass", "fail", "inconclusive"])

    def test_next_higher_speed_row_applies_between_listed_values(self) -> None:
        self.assertEqual(
            maximum_impact_speed_kmh("pedestrian", "M1", "mass_in_running_order", 41.0),
            0.0,
        )
        self.assertEqual(
            maximum_impact_speed_kmh("pedestrian", "M1", "maximum_mass", 41.0),
            10.0,
        )
        self.assertEqual(
            maximum_impact_speed_kmh("bicycle", "N1", "maximum_mass", 37.0),
            15.0,
        )

    def test_out_of_range_and_boolean_speed_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            maximum_impact_speed_kmh("pedestrian", "M1", "maximum_mass", 19.9)
        with self.assertRaises(TypeError):
            maximum_impact_speed_kmh("pedestrian", "M1", "maximum_mass", True)

    def test_fit_measurement_meets_quantified_criteria_without_compliance_claim(self) -> None:
        result = evaluate_regulatory_measurement(_fit_measurement())
        self.assertEqual(result["threshold_result"], "pass")
        self.assertEqual(result["evidence_fitness"], "fit")
        self.assertEqual(result["criterion_result"], "pass")
        self.assertEqual(result["compliance_conclusion"], "withheld")
        self.assertEqual(result["maximum_impact_speed_kmh"], 0.0)

    def test_favorable_numbers_remain_inconclusive_when_target_fidelity_is_missing(self) -> None:
        measurement = _fit_measurement()
        measurement["conditions"]["prescribed_soft_target_fidelity"] = False
        result = evaluate_regulatory_measurement(measurement)
        self.assertEqual(result["threshold_result"], "pass")
        self.assertEqual(result["evidence_fitness"], "inconclusive")
        self.assertEqual(result["criterion_result"], "inconclusive")
        missing = result["unestablished_conditions"]
        if not isinstance(missing, list):
            self.fail("unestablished_conditions must be a list")
        self.assertIn("prescribed_soft_target_fidelity", missing)

    def test_threshold_failure_is_not_hidden_by_fit_evidence(self) -> None:
        measurement = _fit_measurement()
        measurement["impact_speed_kmh"] = 0.1
        result = evaluate_regulatory_measurement(measurement)
        self.assertEqual(result["threshold_result"], "fail")
        self.assertEqual(result["evidence_fitness"], "fit")
        self.assertEqual(result["criterion_result"], "fail")

    def test_two_successful_repetitions_are_required(self) -> None:
        measurement = _fit_measurement()
        measurement["successful_repetitions"] = 1
        result = evaluate_regulatory_measurement(measurement)
        self.assertEqual(result["criterion_result"], "inconclusive")
        missing = result["unestablished_conditions"]
        if not isinstance(missing, list):
            self.fail("unestablished_conditions must be a list")
        self.assertIn("successful_repetitions", missing)

    def test_measurement_shape_is_closed(self) -> None:
        measurement = _fit_measurement()
        measurement["invented"] = "field"
        with self.assertRaisesRegex(ValueError, "measurement keys"):
            evaluate_regulatory_measurement(measurement)


if __name__ == "__main__":
    unittest.main()
