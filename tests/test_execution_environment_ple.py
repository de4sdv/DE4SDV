import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "configure_variant.py"
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
ENGINEERING_FM = PLE_ROOT / "feature-models" / "engineering_execution_environments.yaml"
VEHICLE_FM = PLE_ROOT / "feature-models" / "vehicle_execution_environments.yaml"
SDV_FM = PLE_ROOT / "feature-models" / "sdv_product_line.yaml"
SDV_SHARED_MODEL = (
    REPO_ROOT
    / "textual-notation-of-model"
    / "packages"
    / "architecture"
    / "sdv_platform_stack.sysml"
)
CONFIGURATIONS = {
    "inc-aebs-009a-jetson.yaml": (
        ENGINEERING_FM,
        "inc_aebs_009a_jetson_execution_environment.sysml",
        "inspected",
    ),
    "apple-silicon-macos-candidate.yaml": (
        ENGINEERING_FM,
        "apple_silicon_macos_candidate.sysml",
        "planned",
    ),
    "nxp-zephyr-vehicle-target-candidate.yaml": (
        VEHICLE_FM,
        "nxp_zephyr_vehicle_target_candidate.sysml",
        "planned",
    ),
}


class TestExecutionEnvironmentPle(unittest.TestCase):
    def run_config(self, feature_model, bof, output=None):
        command = [
            sys.executable,
            str(SCRIPT),
            "--feature-model",
            str(feature_model),
            "--bof",
            str(bof),
            "--shared-assets-model",
            str(SHARED_MODEL),
        ]
        if output is None:
            command.append("--check-only")
        else:
            command.extend(["--output", str(output)])
        return subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True)

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
        for config_name, (feature_model, output_name, expected_status) in CONFIGURATIONS.items():
            bof = PLE_ROOT / "feature-configurations" / config_name
            output = PLE_ROOT / "product-models" / output_name
            data = yaml.safe_load(bof.read_text())
            self.assertEqual(data["evidence"]["status"], expected_status)
            with tempfile.NamedTemporaryFile(suffix=".sysml") as generated:
                result = self.run_config(feature_model, bof, generated.name)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(Path(generated.name).read_text(), output.read_text())

    def test_existing_sdv_projections_remain_reproducible(self):
        legacy = {
            "example-linux-score-autoware.yaml": "example_linux_score.sysml",
            "apollo-qnx-qvm.yaml": "apollo_qnx_qvm.sysml",
            "aebs-autoware-linux-lidar-camera.yaml": "aebs_autoware_linux_lidar_camera.sysml",
        }
        for config_name, output_name in legacy.items():
            with self.subTest(configuration=config_name):
                with tempfile.NamedTemporaryFile(suffix=".sysml") as generated:
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(SCRIPT),
                            "--feature-model",
                            str(SDV_FM),
                            "--bof",
                            str(PLE_ROOT / "feature-configurations" / config_name),
                            "--shared-assets-model",
                            str(SDV_SHARED_MODEL),
                            "--output",
                            generated.name,
                        ],
                        cwd=REPO_ROOT,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(
                        Path(generated.name).read_text(),
                        (PLE_ROOT / "product-models" / output_name).read_text(),
                    )

    def test_engineering_compatibility_rules_reject_cross_platform_mix(self):
        configs = PLE_ROOT / "feature-configurations"
        cases = [
            ("apple-silicon-macos-candidate.yaml", "Environment.OperatingSystem", "Ubuntu2204Tegra"),
            ("apple-silicon-macos-candidate.yaml", "Environment.ExecutionRuntime", "NativeLinuxArm64OCI"),
            ("inc-aebs-009a-jetson.yaml", "Environment.OperatingSystem", "MacOSAppleSilicon"),
            ("inc-aebs-009a-jetson.yaml", "Environment.ExecutionRuntime", "VirtualizedLinuxArm64OCIOnMacOS"),
        ]
        for source_name, path, selection in cases:
            with self.subTest(source=source_name, path=path, selection=selection):
                invalid = yaml.safe_load((configs / source_name).read_text())
                invalid["selections"][path] = selection
                with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as bof:
                    yaml.safe_dump(invalid, bof, sort_keys=False)
                    bof.flush()
                    result = self.run_config(ENGINEERING_FM, Path(bof.name))
                self.assertEqual(result.returncode, 1)
                self.assertIn("requires", result.stderr)

    def test_vehicle_compatibility_rules_reject_partial_resolution(self):
        source = yaml.safe_load(
            (
                PLE_ROOT
                / "feature-configurations"
                / "nxp-zephyr-vehicle-target-candidate.yaml"
            ).read_text()
        )
        cases = [
            ("Environment.OperatingSystem", "NoConcreteOperatingSystem"),
            ("Environment.ExecutionRuntime", "NoConcreteExecutionRuntime"),
            ("Environment.ComputeNode", "NoConcreteComputeNode"),
        ]
        for path, selection in cases:
            with self.subTest(path=path, selection=selection):
                invalid = copy.deepcopy(source)
                invalid["selections"][path] = selection
                with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as bof:
                    yaml.safe_dump(invalid, bof, sort_keys=False)
                    bof.flush()
                    result = self.run_config(VEHICLE_FM, Path(bof.name))
                self.assertEqual(result.returncode, 1)
                self.assertIn("requires", result.stderr)

    def test_009a_trace_binds_exact_host_and_retained_evidence(self):
        model = TRACE_MODEL.read_text()
        self.assertIn("INCAEBS009AJetsonExecutionEnvironment", model)
        self.assertIn("NVIDIA Jetson Orin Nano Engineering", model)
        self.assertIn("Reference Developer Kit Super", model)
        self.assertIn("dependency historical009ARuntimeEvidence", model)
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
