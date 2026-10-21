"""The execution-environment families of the product line (ADR 0022).

The engineering (System 2) and vehicle-target (System 1) families are PLEML
feature models with their own configurations. Each committed projection
regenerates from its receipt byte for byte, and each configuration's evidence
record states its evidence status explicitly. The requires constraints of the
two families are evaluated on every selection in
``tests/test_ple_authority_model.py``.
"""
import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SHARED_MODEL = (
    REPO_ROOT
    / "textual-notation-of-model"
    / "packages"
    / "architecture"
    / "execution_environments.sysml"
)
TRACE_MODEL = (
    REPO_ROOT
    / "textual-notation-of-model"
    / "packages"
    / "features"
    / "aebs"
    / "aebs_execution_environment.sysml"
)
PLE_ROOT = REPO_ROOT / "model-based-product-line-engineering"
CONFIGURATIONS_DIR = Path("model-based-product-line-engineering/feature-configurations")
#: Each execution-environment configuration: its projection and the status of its evidence record.
CONFIGURATIONS = {
    "inc_aebs_009a_jetson.sysml": ("inc_aebs_009a_jetson_execution_environment.sysml", "inspected"),
    "apple_silicon_macos_candidate.sysml": ("apple_silicon_macos_candidate.sysml", "planned"),
    "nxp_zephyr_vehicle_target_candidate.sysml": ("nxp_zephyr_vehicle_target_candidate.sysml", "planned"),
}


class TestExecutionEnvironmentPle(unittest.TestCase):
    def test_shared_asset_separates_engineering_and_vehicle_target_families(self):
        model = SHARED_MODEL.read_text()
        self.assertIn("part def EngineeringExecutionEnvironment :> ExecutionEnvironment", model)
        self.assertIn("part def VehicleTargetExecutionEnvironment :> ExecutionEnvironment", model)
        engineering = model.split(
            "part def EngineeringExecutionEnvironment :> ExecutionEnvironment", 1
        )[1].split("part def VehicleTargetExecutionEnvironment", 1)[0]
        vehicle = model.split("part def VehicleTargetExecutionEnvironment", 1)[1]
        self.assertIn("jetsonOrinNano", engineering)
        self.assertIn("appleSiliconMac", engineering)
        self.assertNotIn("nxpVehicleCompute", engineering)
        self.assertIn("nxpVehicleCompute", vehicle)
        self.assertIn("zephyr", vehicle)
        self.assertNotIn("appleSiliconMac", vehicle)

    def test_committed_projections_are_reproducible_and_statuses_are_explicit(self):
        """Each committed projection regenerates from its receipt byte for byte, and the
        evidence record of its configuration states the evidence status."""
        import projection_sources as sources

        for configuration, (output_name, expected_status) in CONFIGURATIONS.items():
            with self.subTest(configuration=configuration):
                committed = (PLE_ROOT / "product-models" / output_name).read_text()
                record = PLE_ROOT / "feature-configurations" / "evidence" / (
                    Path(configuration).stem.replace("_", "-") + ".yaml")
                self.assertEqual(yaml.safe_load(record.read_text())["status"], expected_status)
                self.assertEqual(
                    sources.receipt_projection((CONFIGURATIONS_DIR / configuration).as_posix()), committed
                )

    def test_existing_sdv_projections_remain_reproducible(self):
        """From the receipts, byte for byte."""
        import projection_sources as sources

        legacy = {
            "example_linux_score_autoware.sysml": "example_linux_score.sysml",
            "apollo_qnx_qvm.sysml": "apollo_qnx_qvm.sysml",
            "aebs_autoware_linux_lidar_camera.sysml": "aebs_autoware_linux_lidar_camera.sysml",
        }
        for configuration, output_name in legacy.items():
            with self.subTest(configuration=configuration):
                committed = (PLE_ROOT / "product-models" / output_name).read_text()
                self.assertEqual(
                    sources.receipt_projection((CONFIGURATIONS_DIR / configuration).as_posix()), committed
                )

    def test_009a_trace_binds_exact_host_and_retained_evidence(self):
        model = TRACE_MODEL.read_text()
        self.assertIn("INCAEBS009AJetsonExecutionEnvironment", model)
        self.assertIn("NVIDIA Jetson Orin Nano Engineering", model)
        self.assertIn("Reference Developer Kit Super", model)
        self.assertIn("dependency historicalRuntimeEvidence", model)
        self.assertIn("dependency maintainedHostIdentity", model)
        self.assertIn("runtime-lock.yaml", model)
        self.assertIn("container-identity.json", model)
        self.assertIn("execution-environment-snapshot.json", model)

    def test_009b_and_009c_record_current_bounded_evidence_status(self):
        increments = yaml.safe_load(
            (
                REPO_ROOT
                / "implementation"
                / "aebs-autoware-executable-bench"
                / "increments.yaml"
            ).read_text()
        )["increments"]
        by_id = {item["id"]: item for item in increments}
        self.assertEqual(
            by_id["INC-AEBS-009B"]["status"],
            "merged_replayable_nominal_moving_target_evidence",
        )
        self.assertTrue(
            any(
                "same-lane moving vehicle target" in item
                for item in by_id["INC-AEBS-009B"]["acceptance_boundary"]
            )
        )
        self.assertEqual(
            by_id["INC-AEBS-009C"]["status"],
            "executed_replay_validated_pending_review",
        )
        self.assertTrue(
            any(
                "explicitly partial" in item
                for item in by_id["INC-AEBS-009C"]["acceptance_boundary"]
            )
        )


if __name__ == "__main__":
    unittest.main()
