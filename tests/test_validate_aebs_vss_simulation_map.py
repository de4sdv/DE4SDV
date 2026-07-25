"""Tests for the AEBS VSS-to-simulation realization map."""

import unittest
from pathlib import Path

import yaml

from scripts import validate_aebs_vss_simulation_map as validator


class TestAebsVssSimulationMap(unittest.TestCase):
    def test_repository_map_matches_functional_catalog(self):
        root = Path(__file__).resolve().parents[1]
        functional = yaml.safe_load(
            (root / "methodologies/sysmod-sysmlv2/pilots/aebs-functional-interfaces.yaml").read_text()
        )
        realization = yaml.safe_load(
            (
                root
                / "methodologies/sysmod-sysmlv2/pilots/aebs-simulation-deployment/vss-simulation-realization.yaml"
            ).read_text()
        )

        self.assertEqual(validator.validate_mapping(functional, realization), [])

    def test_accepts_exact_functional_catalog_coverage(self):
        functional = {
            "signal_classification": [
                {
                    "item": "VehicleMotionState",
                    "attribute": "vehicleSpeed",
                    "vss_path": "Vehicle.Speed",
                }
            ]
        }
        realization = {
            "mapping_policy": {"mapping_kinds": {"unit_transform": "conversion"}},
            "mappings": [
                {
                    "id": "VSS-SIM-AEBS-001",
                    "functional_item": "VehicleMotionState",
                    "functional_attribute": "vehicleSpeed",
                    "vss_path": "Vehicle.Speed",
                    "mapping_kind": "unit_transform",
                }
            ],
        }

        self.assertEqual(validator.validate_mapping(functional, realization), [])

    def test_reports_missing_functional_trace(self):
        functional = {
            "signal_classification": [
                {
                    "item": "VehicleMotionState",
                    "attribute": "vehicleSpeed",
                    "vss_path": "Vehicle.Speed",
                }
            ]
        }
        realization = {
            "mapping_policy": {"mapping_kinds": {"unit_transform": "conversion"}},
            "mappings": [],
        }

        self.assertEqual(
            validator.validate_mapping(functional, realization),
            ["missing mapping: VehicleMotionState.vehicleSpeed -> Vehicle.Speed"],
        )

    def test_reports_extra_realization_trace(self):
        functional = {"signal_classification": []}
        realization = {
            "mapping_policy": {"mapping_kinds": {"unit_transform": "conversion"}},
            "mappings": [
                {
                    "id": "VSS-SIM-AEBS-999",
                    "functional_item": "UnknownItem",
                    "functional_attribute": "unknownAttribute",
                    "vss_path": "Vehicle.Unknown",
                    "mapping_kind": "unit_transform",
                }
            ],
        }

        self.assertEqual(
            validator.validate_mapping(functional, realization),
            ["extra mapping: UnknownItem.unknownAttribute -> Vehicle.Unknown"],
        )

    def test_reports_duplicate_mapping_id(self):
        functional = {
            "signal_classification": [
                {"item": "First", "attribute": "value", "vss_path": "Vehicle.First"},
                {"item": "Second", "attribute": "value", "vss_path": "Vehicle.Second"},
            ]
        }
        realization = {
            "mapping_policy": {"mapping_kinds": {"unrealized_gap": "gap"}},
            "mappings": [
                {"id": "DUPLICATE", "functional_item": "First", "functional_attribute": "value", "vss_path": "Vehicle.First", "mapping_kind": "unrealized_gap"},
                {"id": "DUPLICATE", "functional_item": "Second", "functional_attribute": "value", "vss_path": "Vehicle.Second", "mapping_kind": "unrealized_gap"},
            ],
        }

        self.assertEqual(
            validator.validate_mapping(functional, realization),
            ["duplicate mapping id: DUPLICATE"],
        )

    def test_reports_duplicate_functional_trace_with_distinct_ids(self):
        functional = {
            "signal_classification": [
                {"item": "First", "attribute": "value", "vss_path": "Vehicle.First"}
            ]
        }
        realization = {
            "mapping_policy": {"mapping_kinds": {"unrealized_gap": "gap"}},
            "mappings": [
                {
                    "id": "ONE",
                    "functional_item": "First",
                    "functional_attribute": "value",
                    "vss_path": "Vehicle.First",
                    "mapping_kind": "unrealized_gap",
                },
                {
                    "id": "TWO",
                    "functional_item": "First",
                    "functional_attribute": "value",
                    "vss_path": "Vehicle.First",
                    "mapping_kind": "unrealized_gap",
                },
            ],
        }

        self.assertEqual(
            validator.validate_mapping(functional, realization),
            ["duplicate mapping trace: First.value -> Vehicle.First (2 occurrences)"],
        )

    def test_reports_duplicate_functional_catalog_trace(self):
        duplicate = {"item": "First", "attribute": "value", "vss_path": "Vehicle.First"}
        functional = {"signal_classification": [duplicate, duplicate.copy()]}
        realization = {
            "mapping_policy": {"mapping_kinds": {"unrealized_gap": "gap"}},
            "mappings": [
                {
                    "id": "ONE",
                    "functional_item": "First",
                    "functional_attribute": "value",
                    "vss_path": "Vehicle.First",
                    "mapping_kind": "unrealized_gap",
                }
            ],
        }

        self.assertEqual(
            validator.validate_mapping(functional, realization),
            ["duplicate functional trace: First.value -> Vehicle.First (2 occurrences)"],
        )

    def test_reports_undeclared_mapping_kind(self):
        functional = {
            "signal_classification": [
                {"item": "First", "attribute": "value", "vss_path": "Vehicle.First"}
            ]
        }
        realization = {
            "mapping_policy": {"mapping_kinds": {"unrealized_gap": "gap"}},
            "mappings": [
                {
                    "id": "VSS-SIM-AEBS-001",
                    "functional_item": "First",
                    "functional_attribute": "value",
                    "vss_path": "Vehicle.First",
                    "mapping_kind": "invented_kind",
                }
            ],
        }

        self.assertEqual(
            validator.validate_mapping(functional, realization),
            ["undeclared mapping kind: VSS-SIM-AEBS-001 -> invented_kind"],
        )


if __name__ == "__main__":
    unittest.main()
