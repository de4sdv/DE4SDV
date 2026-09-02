import re
import unittest
from pathlib import Path

import yaml

from sysml_shapes import requirement_block, strip_comments


REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE10_MODEL = (
    REPO_ROOT
    / "textual-notation-of-model"
    / "packages"
    / "features"
    / "middleware"
    / "middleware_verification_evidence.sysml"
)
PHASE10_PILOT = (
    REPO_ROOT
    / "methodologies"
    / "sysmod-sysmlv2"
    / "pilots"
    / "middleware-v-and-v-evidence.yaml"
)
BASELINE_REGISTER = REPO_ROOT / "configuration-management" / "baseline-register.md"
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
        cls.baseline_register = BASELINE_REGISTER.read_text()
        cls.cloud_baseline = yaml.safe_load(CLOUD_BASELINE.read_text())
        cls.cloud_evidence = yaml.safe_load(PHASE10_CLOUD_EVIDENCE.read_text())

    def test_phase10_artifacts_and_predecessor_are_explicit(self):
        self.assertTrue(PHASE10_MODEL.is_file())
        self.assertTrue(PHASE10_PILOT.is_file())
        self.assertEqual(self.pilot["id"], "INC-MW-010")
        self.assertEqual(self.pilot["parent_increment"], "INC-MW-009")
        self.assertEqual(self.pilot["status"], "baselined_bounded")
        self.assertTrue(VSIDL_CATALOG_BUILD.is_file())
        self.assertTrue(PHASE10_CLOUD_EVIDENCE.is_file())
        self.assertIn("rust_protobuf", VSIDL_CATALOG_BUILD.read_text())
        self.assertEqual(
            self.pilot["model_artifacts"]["sysml"],
            "textual-notation-of-model/packages/features/middleware/"
            "middleware_verification_evidence.sysml",
        )

    def test_phase12_bounded_baseline_is_explicit_and_controlled(self):
        baseline = self.pilot["phase12_baseline"]
        self.assertEqual(
            set(baseline),
            {
                "id",
                "sysml_element",
                "status",
                "recorded_on",
                "evidence",
                "deferred_items",
                "successor_decision",
            },
        )
        self.assertEqual(baseline["id"], "BL-MW-010-P12")
        self.assertEqual(baseline["sysml_element"], "boundedBaselineDecision010")
        self.assertEqual(baseline["status"], "accepted_bounded")
        self.assertEqual(str(baseline["recorded_on"]), "2026-08-27")
        self.assertEqual(
            {item["id"] for item in baseline["evidence"]},
            {"E-MW-011", "E-MW-012", "E-MW-013", "E-MW-014"},
        )
        self.assertTrue(
            all(set(item) == {"id", "artifact", "status"} for item in baseline["evidence"])
        )
        for evidence in baseline["evidence"]:
            with self.subTest(evidence=evidence["id"]):
                artifact = REPO_ROOT / evidence["artifact"]
                self.assertTrue(artifact.is_file(), f"missing {artifact}")
                self.assertIn(evidence["artifact"], self.model)
        self.assertEqual(
            baseline["deferred_items"],
            [
                {"id": "AC-MW-010-02", "status": "deferred_not_proven"},
                {"id": "AC-MW-010-05", "status": "deferred_not_proven"},
                {"gate": 8, "status": "not_claimed"},
            ],
        )
        self.assertEqual(
            baseline["successor_decision"], "successorIncrementDecision010"
        )

        self.assertIn(
            "part boundedBaselineDecision010 : IncrementLifecycleDecision", self.model
        )
        self.assertIn(
            "part successorIncrementDecision010 : IncrementLifecycleDecision", self.model
        )
        self.assertIn("runtimeAdapterPathEvidence012", self.model)
        self.assertIn("runtimeAutowareConsumerEvidence013", self.model)
        self.assertIn("runtimeHealthDispositionEvidence014", self.model)
        self.assertIn("boundedClaimToBaselineDecision010", self.model)
        self.assertIn("deferredLifecycleCounterclaimToBaselineDecision010", self.model)
        self.assertNotIn("dependency claimSupportedByLifecycleArgument", self.model)
        self.assertNotIn("dependency claimSupportedByUpdateArgument", self.model)

        self.assertIn("Status: controlled", self.baseline_register)
        self.assertNotIn("BL-001", self.baseline_register)
        self.assertRegex(
            self.baseline_register,
            r"\| BL-MW-010-P12 \| System 1 \+ System 2 \|[^\n]+"
            r"\| INC-MW-010@Phase12 \| 2026-08-27 \| "
            r"boundedBaselineDecision010 \| E-MW-011; E-MW-012; E-MW-013; E-MW-014 \|",
        )

    def test_phase12_status_index_matches_bounded_verdicts(self):
        self.assertEqual(
            self.pilot["system_boundary"]["system_1_member_product"]["runtime_status"],
            "observed_bounded_two_vm_campaign",
        )
        case_statuses = {
            case["id"]: case["status"] for case in self.pilot["verification_cases"]
        }
        self.assertEqual(
            case_statuses,
            {
                "VC-MW-010-01": "pass_bounded_verification",
                "VC-MW-010-02": "deferred_not_proven",
                "VC-MW-010-03": "pass_bounded_verification",
                "VC-MW-010-04": "pass_bounded_verification",
                "VC-MW-010-05": "deferred_not_proven",
                "VC-MW-010-06": "pass_bounded_verification",
            },
        )
        criterion_statuses = {
            criterion["id"]: criterion["status"]
            for criterion in self.pilot["acceptance_criteria"]
        }
        self.assertEqual(criterion_statuses["AC-MW-010-02"], "deferred_not_proven")
        self.assertEqual(criterion_statuses["AC-MW-010-05"], "deferred_not_proven")
        self.assertNotIn("not_yet_realized", PHASE10_PILOT.read_text())
        self.assertNotIn("planned_target_runtime_case", PHASE10_PILOT.read_text())
        self.assertEqual(
            self.pilot["claim_boundary"],
            {
                "sysml_element": "boundedBaselineDecision010",
                "status": "accepted_bounded",
            },
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
        criterion = self.pilot["acceptance_criteria"][0]
        self.assertEqual(criterion["id"], "AC-MW-010-01")
        self.assertEqual(criterion["status"], "pass_bounded_verification")
        self.assertEqual(criterion["evidence"], "E-MW-011 gates 4-6")
        # The semantic content lives in the model, not the pilot YAML.
        self.assertNotIn("statement", criterion)
        self.assertIn("division by 3.6", self.model)
        self.assertIn("independent observer", self.model)

    def test_acceptance_criteria_trace_to_sysml_and_do_not_fake_runtime_passes(self):
        criteria = self.pilot["acceptance_criteria"]
        self.assertEqual(len(criteria), 7)
        for criterion in criteria:
            with self.subTest(criterion=criterion["id"]):
                # Status-only entries: id + sysml_element + status + evidence
                # index (evidence references E-MW-011 gates; no statement text).
                self.assertEqual(
                    set(criterion), {"id", "sysml_element", "status", "evidence"}
                )
                self.assertIn(criterion["sysml_element"], self.model)

        statuses = {criterion["status"] for criterion in criteria}
        self.assertIn("deferred_not_proven", statuses)
        self.assertIn("pass_bounded_verification", statuses)
        self.assertNotIn("accepted", statuses)
        self.assertNotIn("pass_target_runtime", statuses)
        self.assertIn("Missing target-runtime evidence", self.model)
        self.assertIn("never a runtime pass", self.model)

    def test_verification_cases_are_status_only_references(self):
        # No semantic restatement in the pilot YAML: cases reference the model
        # by scenario/acceptance_criterion and carry status, not content.
        allowed = {
            "id", "name", "scenario", "requirement_ids", "methods",
            "acceptance_criterion", "status", "current_evidence",
            "missing_evidence",
        }
        for case in self.pilot["verification_cases"]:
            with self.subTest(case=case["id"]):
                self.assertTrue(set(case) <= allowed)
                self.assertIn(case["scenario"], self.model)
                self.assertIn(case["acceptance_criterion"], self.model)

    def test_acceptance_criteria_semantics_owned_by_model(self):
        # Content-level guard: every criterion the pilot references must exist
        # in the model as a requirement with a non-trivial constraint text.
        criteria = self.pilot["acceptance_criteria"]
        for criterion in criteria:
            element = criterion["sysml_element"]
            with self.subTest(criterion=criterion["id"], element=element):
                block = requirement_block(self.model, element)
                self.assertIsNotNone(block, f"{element} not found in model")
                assert block is not None  # for type checkers
                self.assertIn("require constraint", block)
                constraint_text = strip_comments(block)
                self.assertGreater(len(constraint_text.strip()), 40)

    def test_evidence_ladder_preserves_claim_boundaries(self):
        layers = {layer["layer"]: layer for layer in self.pilot["evidence_ladder"]}
        self.assertEqual(layers["unit_and_contract_tests"]["status"], "observed_bounded")
        self.assertEqual(layers["reference_rehearsal"]["status"], "observed_bounded")
        self.assertEqual(layers["aaos_cuttlefish_boot"]["status"], "observed_bounded")
        self.assertEqual(
            layers["target_runtime_interoperability"]["status"],
            "observed_bounded_autoware_consumer",
        )
        self.assertEqual(
            layers["lifecycle_update_fault_validation"]["status"],
            "partial_health_observed",
        )
        self.assertIn("ArgumentationAssuranceViewpoint", self.model)
        self.assertNotIn("PhysicalStructureDefinitionViewpoint", self.model)

    def test_cloud_vm_is_system2_candidate_with_readiness_and_cost_gates(self):
        cloud = self.pilot["cloud_readiness"]
        self.assertEqual(cloud["candidate"], "google-cloud-x86_64-linux-nested-kvm")
        self.assertEqual(cloud["provisioning_status"], "observed_bounded_campaign")
        self.assertEqual(cloud["campaign_instance"], "de4sdv-aaos-build")
        self.assertEqual(cloud["campaign_state_after"], "TERMINATED")
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
            "runtimeCampaignEvidence011",
            "reqMaintainMiddlewareBoundaryTraceability",
        ]
        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, self.model)


if __name__ == "__main__":
    unittest.main()
