"""Tests for the AEBS VSS-to-simulation realization map."""

import unittest
from pathlib import Path

import yaml

from scripts import validate_aebs_vss_simulation_map as validator

ROOT = Path(__file__).resolve().parents[1]
REALIZATION = ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-simulation-deployment/vss-simulation-realization.yaml"


def _signal(name: str, path: str) -> str:
    """One signal as the VSS libraries declare it."""
    return (
        f"  attribute def {name} :> Boolean;\n"
        f"  @VssSignalMetadata about {name} {{\n"
        f'    path = "{path}";\n'
        '    kind = "sensor";\n'
        "  }\n"
    )


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


class TestAebsVssSimulationMapSources(unittest.TestCase):
    """The map against the two VSS libraries it names as its source baselines."""

    COMMIT = "a" * 40
    LIBRARY = (
        "/*\n"
        f" * Source: https://github.com/COVESA/vehicle_signal_specification/tree/{COMMIT}/spec\n"
        " */\n"
        "package COVESA_VSS {\n" + _signal("Vehicle_Speed", "Vehicle.Speed") + "}\n"
    )
    EXTENSIONS = "package DE4SDV_VSS_Extensions {\n" + _signal("Vehicle_Candidate", "Vehicle.Candidate") + "}\n"

    def _realization(self, commit=COMMIT, mappings=(("ONE", "covesa", "Vehicle.Speed"),)):
        return {
            "source_baselines": {"covesa_vss": {"commit": commit}},
            "mappings": [{"id": i, "vss_origin": origin, "vss_path": path} for i, origin, path in mappings],
        }

    def _repository(self):
        realization = yaml.safe_load(REALIZATION.read_text(encoding="utf-8"))
        baselines = realization["source_baselines"]
        library = (ROOT / baselines["covesa_vss"]["local_library"]).read_text(encoding="utf-8")
        extensions = (ROOT / baselines["de4sdv_vss_extensions"]["path"]).read_text(encoding="utf-8")
        return realization, library, extensions

    def test_repository_map_names_the_source_commit_of_its_library(self):
        realization, library, _ = self._repository()
        self.assertEqual(validator.validate_source_baseline(realization, library), [])

    def test_repository_map_uses_only_signals_its_libraries_declare(self):
        realization, library, extensions = self._repository()
        self.assertEqual(validator.validate_vss_paths(realization, library, extensions), [])

    def test_accepts_the_source_commit_and_the_declared_signals(self):
        realization = self._realization(
            mappings=(("ONE", "covesa", "Vehicle.Speed"), ("TWO", "de4sdv_candidate", "Vehicle.Candidate"))
        )
        self.assertEqual(validator.validate_source_baseline(realization, self.LIBRARY), [])
        self.assertEqual(validator.validate_vss_paths(realization, self.LIBRARY, self.EXTENSIONS), [])

    def test_reports_a_commit_other_than_the_library_source_commit(self):
        other = "b" * 40
        self.assertEqual(
            validator.validate_source_baseline(self._realization(commit=other), self.LIBRARY),
            [f"covesa_vss commit {other} is not the library's source commit {self.COMMIT}"],
        )

    def test_reports_a_library_that_does_not_state_one_source_commit(self):
        source_line = f" * Source: https://github.com/COVESA/vehicle_signal_specification/tree/{self.COMMIT}/spec\n"
        libraries = {0: self.LIBRARY.replace(source_line, ""), 2: self.LIBRARY.replace(source_line, source_line * 2)}
        for count, library in libraries.items():
            with self.subTest(source_lines=count):
                self.assertEqual(library.count(source_line), count)
                self.assertEqual(
                    validator.validate_source_baseline(self._realization(), library),
                    [f"library states {count} source commits, expected 1"],
                )

    def test_reports_a_path_that_the_library_of_its_origin_does_not_declare(self):
        realization = self._realization(
            mappings=(
                ("GONE", "covesa", "Vehicle.Removed"),
                ("WRONG-ORIGIN", "covesa", "Vehicle.Candidate"),
                ("WRONG-ORIGIN-TOO", "de4sdv_candidate", "Vehicle.Speed"),
            )
        )
        self.assertEqual(
            validator.validate_vss_paths(realization, self.LIBRARY, self.EXTENSIONS),
            [
                "vss_path is not a signal of the covesa library: GONE -> Vehicle.Removed",
                "vss_path is not a signal of the covesa library: WRONG-ORIGIN -> Vehicle.Candidate",
                "vss_path is not a signal of the de4sdv_candidate library: WRONG-ORIGIN-TOO -> Vehicle.Speed",
            ],
        )

    def test_reports_an_origin_without_a_library(self):
        realization = self._realization(
            mappings=(("ONE", "elsewhere", "Vehicle.Speed"), ("TWO", None, "Vehicle.Speed"))
        )
        self.assertEqual(
            validator.validate_vss_paths(realization, self.LIBRARY, self.EXTENSIONS),
            ["unknown vss_origin: ONE -> elsewhere", "unknown vss_origin: TWO -> None"],
        )

    def test_a_signal_inside_a_comment_is_not_declared(self):
        library = self.LIBRARY.replace(
            _signal("Vehicle_Speed", "Vehicle.Speed"), "/*\n" + _signal("Vehicle_Speed", "Vehicle.Speed") + "*/\n"
        )
        self.assertNotEqual(library, self.LIBRARY)
        self.assertEqual(
            validator.validate_vss_paths(self._realization(), library, self.EXTENSIONS),
            ["vss_path is not a signal of the covesa library: ONE -> Vehicle.Speed"],
        )


if __name__ == "__main__":
    unittest.main()
