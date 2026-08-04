import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
PLE_ROOT = REPO_ROOT / "model-based-product-line-engineering"
FEATURE_MODEL = PLE_ROOT / "feature-models" / "sdv_product_line.yaml"
BOF = PLE_ROOT / "feature-configurations" / "mw-autoware-aaos-sdv-reference.yaml"
PRODUCT_MODEL = PLE_ROOT / "product-models" / "mw_autoware_aaos_sdv_reference.sysml"
SHARED_MODEL = (
    REPO_ROOT
    / "textual-notation-of-model"
    / "packages"
    / "architecture"
    / "sdv_platform_stack.sysml"
)
PHASE9_MODEL = (
    REPO_ROOT
    / "textual-notation-of-model"
    / "packages"
    / "features"
    / "middleware"
    / "mw_variability_configuration.sysml"
)
PILOT = (
    REPO_ROOT
    / "methodologies"
    / "sysmod-sysmlv2"
    / "pilots"
    / "mw-variability-configuration.yaml"
)
CONFIGURATOR = REPO_ROOT / "tools" / "configure_variant.py"


class TestMWVariabilityConfiguration(unittest.TestCase):
    def test_bof_selects_member_features_but_not_the_derived_adapter(self):
        data = yaml.safe_load(BOF.read_text())
        selections = data["selections"]
        self.assertEqual(selections["PlatformStack.VehicleApplication"], "Autoware")
        self.assertEqual(selections["PlatformStack.Middleware"], "AndroidSDV")
        self.assertEqual(selections["PlatformStack.OS"], "Android")
        self.assertEqual(selections["PlatformStack.Hypervisor"], "KVM")
        self.assertEqual(
            selections["SensingBoundary.PerceptionSensors"],
            ["LiDAR", "Camera"],
        )
        self.assertFalse(any("Adapter" in path for path in selections))
        self.assertEqual(data["evidence"]["status"], "planned")
        self.assertEqual(data["evidence"]["artifacts"], [])

    def test_feature_model_derives_the_complete_supported_pair_table(self):
        data = yaml.safe_load(FEATURE_MODEL.read_text())
        derivations = data["derived_asset_selections"]
        self.assertEqual(len(derivations), 1)
        derivation = derivations[0]
        self.assertEqual(
            derivation["maps_to"],
            "SDVPlatformStack.applicationMiddlewareAdapter",
        )
        self.assertEqual(
            derivation["source_selections"],
            [
                "PlatformStack.VehicleApplication",
                "PlatformStack.Middleware",
            ],
        )
        resolved = {
            (
                rule["when"]["PlatformStack.VehicleApplication"],
                rule["when"]["PlatformStack.Middleware"],
            ): rule["maps_to_variant"]
            for rule in derivation["rules"]
        }
        self.assertEqual(
            resolved,
            {
                ("Autoware", "EclipseSCORE"): "autowareToSCORE",
                ("Autoware", "AndroidSDV"): "autowareToAAOSSDV",
                ("Autoware", "AUTOSARAdaptive"): "autowareToAUTOSAR",
                ("Openpilot", "EclipseSCORE"): "openpilotToSCORE",
                ("Apollo", "EclipseSCORE"): "apolloToSCORE",
                ("Autoware", "None"): "none",
                ("Openpilot", "None"): "none",
                ("Apollo", "None"): "none",
            },
        )

    def test_committed_product_projection_is_reproducible(self):
        with tempfile.NamedTemporaryFile(suffix=".sysml") as generated:
            result = subprocess.run(
                [
                    sys.executable,
                    str(CONFIGURATOR),
                    "--feature-model",
                    str(FEATURE_MODEL),
                    "--bof",
                    str(BOF),
                    "--shared-assets-model",
                    str(SHARED_MODEL),
                    "--output",
                    generated.name,
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(generated.name).read_text(), PRODUCT_MODEL.read_text())

        product = PRODUCT_MODEL.read_text()
        self.assertIn(
            "part :>> applicationMiddlewareAdapter = "
            "applicationMiddlewareAdapter::autowareToAAOSSDV;",
            product,
        )
        self.assertIn("derived by D-ASSET-APPLICATION-MIDDLEWARE-ADAPTER", product)
        self.assertIn("do not prove provider", product)
        self.assertNotIn("kuksa", product.lower())

    def test_phase9_model_records_source_roles_realization_choice_and_nonclaims(self):
        model = PHASE9_MODEL.read_text()
        normalized = " ".join(model.replace("*", " ").split())
        required = [
            "package DE4SDV_MWVariabilityConfiguration",
            "part incMW009 : FeatureIncrement",
            "part configuredMember : MWAutowareAAOSSDVConfiguredMember",
            "part ifexInterfaceDesignSource : SourceContributionRecord",
            "part vehicleSpeedPropertyClassification : SourceContributionRecord",
            "part directVSIDLToROS2Realization : MissingRealizationRecord",
            "part kuksaBrokeredAlternative : DeferredProductLineScope",
            "dependency configuredPhysicalBoundaryTrace",
            "dependency vssVehicleSpeedSemanticTrace",
            "dependency exactReferenceContractTrace",
            "ProductLineConfigurationViewpoint",
            "ProductModelAssemblyViewpoint",
            "GAP-MW-024",
        ]
        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, model)
        self.assertIn("Property", model)
        self.assertIn("not selected", model)
        self.assertIn("not implemented", normalized)
        self.assertIn("not deployed", normalized)
        self.assertIn("not empirically verified", normalized)
        self.assertNotIn("part kuksaDatabroker", model)

    def test_pilot_is_framing_metadata_not_a_second_configuration_model(self):
        data = yaml.safe_load(PILOT.read_text())
        self.assertEqual(data["id"], "INC-MW-009")
        self.assertEqual(data["parent_increment"], "INC-MW-008")
        self.assertEqual(
            data["model_artifacts"]["bill_of_features"],
            "model-based-product-line-engineering/feature-configurations/"
            "mw-autoware-aaos-sdv-reference.yaml",
        )
        self.assertNotIn("selections", data)
        self.assertNotIn("derived_adapter", data)
        self.assertIn("INC-MW-010", data["next_increments"])


if __name__ == "__main__":
    unittest.main()
