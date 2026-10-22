"""INC-MW-009: the configured Autoware + AAOS SDV member (ADR 0022).

The member's PLEML feature configuration selects the application and the
middleware; the receipt derives the adapter, which no configuration selects;
the committed projection regenerates from the receipt byte for byte.
"""
import json
import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
PLE_ROOT = REPO_ROOT / "model-based-product-line-engineering"
FEATURE_MODEL = PLE_ROOT / "feature-models" / "sdv_product_line.sysml"
CONFIGURATION = PLE_ROOT / "feature-configurations" / "middleware_autoware_aaos_sdv_reference.sysml"
EVIDENCE_RECORD = PLE_ROOT / "feature-configurations" / "evidence" / "middleware-autoware-aaos-sdv-reference.yaml"
RECEIPT = PLE_ROOT / "feature-models" / "receipts" / "sdv_product_line.receipt.json"
PRODUCT_MODEL = PLE_ROOT / "product-models" / "middleware_autoware_aaos_sdv_reference.sysml"
PHASE9_MODEL = (
    REPO_ROOT
    / "textual-notation-of-model"
    / "packages"
    / "features"
    / "middleware"
    / "middleware_variability_configuration.sysml"
)
PILOT = (
    REPO_ROOT
    / "methodologies"
    / "sysmod-sysmlv2"
    / "pilots"
    / "middleware-variability-configuration.yaml"
)


def _receipt_model():
    receipt = json.loads(RECEIPT.read_text())
    [model] = receipt["evaluation"]["feature_models"]
    return model


class TestMWVariabilityConfiguration(unittest.TestCase):
    def test_configuration_selects_member_features_but_not_the_derived_adapter(self):
        model = _receipt_model()
        [configuration] = [item for item in model["configurations"]
                           if item["source"] == CONFIGURATION.relative_to(REPO_ROOT).as_posix()]
        self.assertTrue(configuration["valid"])
        # One SoC (owner decision D3, INC-MW-011 phase 9): Autoware on Linux on the main side, the KVM host,
        # and the AAOS SDV middleware in the Android guest; no HMI display.
        self.assertEqual(
            {"platformStack.autoware", "platformStack.androidSDV", "platformStack.linux", "platformStack.kvm",
             "platformStack.guestAndroid", "platformStack.guestAndroidSDV",
             "sensingBoundary.lidar", "sensingBoundary.camera"} - set(configuration["selected"]),
            set(),
        )
        self.assertFalse({"platformStack.noMiddleware", "platformStack.android", "platformStack.noGuestOS",
                          "platformStack.noGuestMiddleware", "capabilities.hmiDisplay", "sensingBoundary.radar"}
                         & set(configuration["selected"]))
        exempted = [item["asset"] for item in configuration["admission"]["common_content"] if item["exempted"]]
        self.assertEqual(exempted, [], "the member needs no exemption")
        self.assertFalse(any("adapter" in path.lower() for path in configuration["selected"]))
        derived = {item["variation"]: item for item in configuration["derived_variants"]}
        self.assertEqual(derived["applicationMiddlewareAdapter"]["variant"], "autowareToAAOSSDV")
        self.assertNotIn("binding", derived["applicationMiddlewareAdapter"])
        self.assertEqual(configuration["admission"]["alternative"], "aaosIntegrated")
        evidence = yaml.safe_load(EVIDENCE_RECORD.read_text())
        self.assertEqual(evidence, {"status": "planned", "artifacts": []})

    def test_feature_model_derives_the_complete_supported_pair_table(self):
        [derivation] = _receipt_model()["derivations"]
        self.assertEqual(derivation["derived_variation"], "applicationMiddlewareAdapter")
        resolved = {tuple(rule["premises"]): rule["result"] for rule in derivation["rules"]}
        self.assertEqual(
            resolved,
            {
                ("platformStack.autoware", "platformStack.eclipseSCORE"): "autowareToSCORE",
                ("platformStack.autoware", "platformStack.androidSDV"): "autowareToAAOSSDV",
                ("platformStack.autoware", "platformStack.autosarAdaptive"): "autowareToAUTOSAR",
                ("platformStack.openpilot", "platformStack.eclipseSCORE"): "openpilotToSCORE",
                ("platformStack.apollo", "platformStack.eclipseSCORE"): "apolloToSCORE",
                ("platformStack.autoware", "platformStack.noMiddleware"): "none",
                ("platformStack.openpilot", "platformStack.noMiddleware"): "none",
                ("platformStack.apollo", "platformStack.noMiddleware"): "none",
            },
        )

    def test_committed_product_projection_is_reproducible(self):
        """From the receipt, byte for byte."""
        import projection_sources as sources

        committed = PRODUCT_MODEL.read_text()
        self.assertEqual(sources.receipt_projection(CONFIGURATION.relative_to(REPO_ROOT).as_posix()), committed)

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
            "package DE4SDV_MiddlewareVariabilityConfiguration",
            "part incMW009 : FeatureIncrement",
            "part configuredMember : MiddlewareAutowareAAOSSDVConfiguredMember",
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
        artifacts = data["model_artifacts"]
        self.assertEqual(artifacts["feature_model"], FEATURE_MODEL.relative_to(REPO_ROOT).as_posix())
        self.assertEqual(artifacts["feature_configuration"], CONFIGURATION.relative_to(REPO_ROOT).as_posix())
        self.assertEqual(artifacts["evidence_record"], EVIDENCE_RECORD.relative_to(REPO_ROOT).as_posix())
        for key in ("sysml", "feature_model", "feature_configuration", "evidence_record", "generated_projection"):
            self.assertTrue((REPO_ROOT / artifacts[key]).is_file(), key)
        self.assertNotIn("selections", data)
        self.assertNotIn("derived_adapter", data)
        self.assertIn("INC-MW-010", data["next_increments"])


if __name__ == "__main__":
    unittest.main()
