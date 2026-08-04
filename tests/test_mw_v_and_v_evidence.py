import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE10_MODEL = (
    REPO_ROOT
    / "textual-notation-of-model"
    / "packages"
    / "features"
    / "middleware"
    / "mw_verification_evidence.sysml"
)
PHASE10_PILOT = (
    REPO_ROOT
    / "methodologies"
    / "sysmod-sysmlv2"
    / "pilots"
    / "mw-v-and-v-evidence.yaml"
)
CLOUD_BASELINE = (
    REPO_ROOT
    / "implementation"
    / "aaos-sdv-reference-interop-bench"
    / "evidence"
    / "aaos-cuttlefish-cloud-proof.yaml"
)
PHASE10_CLOUD_EVIDENCE = (
    REPO_ROOT
    / "implementation"
    / "aaos-sdv-reference-interop-bench"
    / "evidence"
    / "mw-010-google-cloud-vsidlc-cuttlefish.yaml"
)
VSIDL_CATALOG_BUILD = (
    REPO_ROOT
    / "implementation"
    / "aaos-sdv-reference-interop-bench"
    / "contract"
    / "Android.bp"
)


class TestMWVerificationAndValidationEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = PHASE10_MODEL.read_text()
        cls.pilot = yaml.safe_load(PHASE10_PILOT.read_text())
        cls.cloud_baseline = yaml.safe_load(CLOUD_BASELINE.read_text())
        cls.cloud_evidence = yaml.safe_load(PHASE10_CLOUD_EVIDENCE.read_text())

    def test_phase10_artifacts_and_predecessor_are_explicit(self):
        self.assertTrue(PHASE10_MODEL.is_file())
        self.assertTrue(PHASE10_PILOT.is_file())
        self.assertEqual(self.pilot["id"], "INC-MW-010")
        self.assertEqual(self.pilot["parent_increment"], "INC-MW-009")
        self.assertEqual(self.pilot["status"], "draft")
        self.assertTrue(VSIDL_CATALOG_BUILD.is_file())
        self.assertTrue(PHASE10_CLOUD_EVIDENCE.is_file())
        self.assertIn("rust_protobuf", VSIDL_CATALOG_BUILD.read_text())
        self.assertEqual(
            self.pilot["model_artifacts"]["sysml"],
            "textual-notation-of-model/packages/features/middleware/"
            "mw_verification_evidence.sysml",
        )

    def test_all_requested_verification_and_validation_scenarios_exist(self):
        cases = self.pilot["verification_cases"]
        self.assertEqual(
            {case["scenario"] for case in cases},
            {
                "signalTranslation",
                "lifecycleCoordination",
                "healthForwarding",
                "vehicleStartup",
                "updateCoordination",
                "faultDetection",
            },
        )
        self.assertEqual(
            {case["id"] for case in cases},
            {
                "VC-MW-010-01",
                "VC-MW-010-02",
                "VC-MW-010-03",
                "VC-MW-010-04",
                "VC-MW-010-05",
                "VC-MW-010-06",
            },
        )
        self.assertIn("Vehicle.Speed", self.model)
        self.assertIn("VehicleStartupValidation010", self.model)
        self.assertIn("UpdateCoordinationValidation010", self.model)
        self.assertIn("FaultDetectionValidation010", self.model)

    def test_signal_translation_criterion_is_deterministic_and_bounded(self):
        signal_case = self.pilot["verification_cases"][0]
        self.assertEqual(signal_case["deterministic_examples"], [
            {"input_kmh": 36, "expected_mps": 10},
            {"input_kmh": 72, "expected_mps": 20},
        ])
        criterion = self.pilot["acceptance_criteria"][0]
        self.assertEqual(criterion["id"], "AC-MW-010-01")
        self.assertEqual(criterion["status"], "partial_lower_layer_evidence")
        self.assertIn("speed_kmh / 3.6", criterion["statement"])
        self.assertIn("independent observation", criterion["statement"])

    def test_acceptance_criteria_trace_to_sysml_and_do_not_fake_runtime_passes(self):
        criteria = self.pilot["acceptance_criteria"]
        self.assertEqual(len(criteria), 7)
        for criterion in criteria:
            with self.subTest(criterion=criterion["id"]):
                self.assertTrue(criterion["statement"])
                self.assertIn(criterion["sysml_element"], self.model)

        statuses = {criterion["status"] for criterion in criteria}
        self.assertIn("blocked_target_runtime", statuses)
        self.assertNotIn("accepted", statuses)
        self.assertNotIn("pass_target_runtime", statuses)
        self.assertIn("Missing target-runtime evidence", self.model)
        self.assertIn("never a runtime pass", self.model)

    def test_evidence_ladder_preserves_claim_boundaries(self):
        layers = {layer["layer"]: layer for layer in self.pilot["evidence_ladder"]}
        self.assertEqual(layers["unit_and_contract_tests"]["status"], "observed_bounded")
        self.assertEqual(layers["reference_rehearsal"]["status"], "observed_bounded")
        self.assertEqual(layers["aaos_cuttlefish_boot"]["status"], "observed_bounded")
        self.assertEqual(layers["target_runtime_interoperability"]["status"], "blocked")
        self.assertEqual(layers["lifecycle_update_fault_validation"]["status"], "blocked")
        self.assertIn("ArgumentationAssuranceViewpoint", self.model)
        self.assertNotIn("PhysicalStructureDefinitionViewpoint", self.model)

    def test_cloud_vm_is_system2_candidate_with_readiness_and_cost_gates(self):
        cloud = self.pilot["cloud_readiness"]
        self.assertEqual(cloud["candidate"], "google-cloud-x86_64-linux-nested-kvm")
        self.assertEqual(cloud["provisioning_status"], "not_started")
        self.assertEqual(cloud["required_capabilities"]["minimum_memory_gib"], 64)
        self.assertEqual(cloud["required_capabilities"]["minimum_free_storage_gib"], 400)
        self.assertTrue(cloud["required_capabilities"]["nested_kvm"])
        self.assertIn("bounded_run_duration", cloud["cost_control_required"])
        self.assertIn("automatic_stop_or_termination", cloud["cost_control_required"])
        self.assertEqual(
            cloud["previous_baseline"]["observed_target"],
            "sdv_core_cf-trunk_staging-userdebug",
        )
        self.assertEqual(self.cloud_baseline["claim"]["not_proven"][0], "the default Cuttlefish vsock ADB path for this target")
        self.assertIn(
            "VSIDL provider deployment or generated vehicle-service bindings",
            self.cloud_baseline["claim"]["not_proven"],
        )

    def test_cloud_evidence_records_compilation_without_runtime_upgrade(self):
        evidence = self.cloud_evidence
        self.assertEqual(evidence["increment"], "INC-MW-010")
        self.assertEqual(evidence["status"], "partial")
        self.assertEqual(evidence["cloud"]["state_after_campaign"], "TERMINATED")
        self.assertTrue(evidence["cloud"]["persistent_disk_retained"])
        self.assertEqual(
            evidence["toolchain"]["vsidlc_catalog_with_android_bp"]["exit_code"],
            0,
        )
        self.assertEqual(
            evidence["cuttlefish"]["service_presence"]["vsidl_provider_agent"],
            "absent",
        )
        self.assertIn("end_to_end_vehicle_speed_interoperability", evidence["not_proven"])
        self.assertTrue(all(item["status"] == "blocked" for item in evidence["execution_evidence"]["blocked"]))

    def test_runtime_gaps_have_owned_next_actions_and_model_elements(self):
        gaps = self.pilot["runtime_evidence_gaps"]
        self.assertEqual(
            {gap["id"] for gap in gaps},
            {"GAP-MW-025", "GAP-MW-026", "GAP-MW-027", "GAP-MW-028"},
        )
        for gap in gaps:
            with self.subTest(gap=gap["id"]):
                self.assertTrue(gap["owner"])
                self.assertTrue(gap["next_action"])
                self.assertIn(gap["model_element"], self.model)

    def test_model_traces_configured_member_requirements_and_evidence(self):
        required = [
            "part incMW010 : FeatureIncrement",
            "MiddlewareIntegrationVandVBench010",
            "acceptanceCriterion010SignalTranslation",
            "acceptanceCriterion010LifecycleCoordination",
            "acceptanceCriterion010HealthForwarding",
            "acceptanceCriterion010VehicleStartup",
            "acceptanceCriterion010UpdateCoordination",
            "acceptanceCriterion010FaultDetection",
            "acceptanceCriterion010EvidenceIndependence",
            "verificationConfiguredMemberTrace",
            "verificationPhysicalBoundaryTrace",
            "verificationExecutionEnvironmentTrace",
            "boundedBootBaselineTrace",
            "plannedTargetRuntimeEvidence010",
            "reqMaintainMiddlewareBoundaryTraceability",
        ]
        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, self.model)


if __name__ == "__main__":
    unittest.main()
