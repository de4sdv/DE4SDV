"""Contract tests for the static INC-AEBS-009A executable-bench scaffold."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

import yaml

from scripts import validate_aebs_executable_bench as validator


ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "implementation/aebs-autoware-executable-bench"


class TestAebsExecutableBench(unittest.TestCase):
    def test_repository_scaffold_satisfies_contract(self):
        self.assertEqual(validator.validate_bench(ROOT), [])

    def test_absent_scaffold_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            errors = validator.validate_bench(Path(directory))
        self.assertTrue(any("missing required artifact" in error for error in errors))

    def _copy_reviewable_bench(self, directory: str) -> Path:
        destination = Path(directory) / "bench"
        shutil.copytree(
            BENCH,
            destination,
            ignore=shutil.ignore_patterns(
                "workspace", "__pycache__", "*.pyc", "*.log", "readiness-ros.json"
            ),
        )
        # The authoritative lock and packaged YAML files must not be ignored.
        for relative in (
            "runtime-lock.yaml",
            "increments.yaml",
            "src/de4sdv_aebs_bench/config/aebs.param.yaml",
            "src/de4sdv_aebs_bench/config/diagnostic-graph.yaml",
            "src/de4sdv_aebs_bench/config/lanelet2_map_loader.param.yaml",
            "src/de4sdv_aebs_bench/config/map_projection_loader.param.yaml",
            "src/de4sdv_aebs_bench/config/map_tf_generator.param.yaml",
            "src/de4sdv_aebs_bench/config/pointcloud_map_loader.param.yaml",
        ):
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(BENCH / relative, target)
        (destination / "workspace").mkdir()
        (destination / "workspace/.gitkeep").touch()
        return destination

    def test_evidence_rejects_changed_execution_input(self):
        with tempfile.TemporaryDirectory() as directory:
            bench = self._copy_reviewable_bench(directory)
            launch = bench / "scripts/launch.sh"
            launch.write_text(launch.read_text() + "\n# post-execution mutation\n")
            lock = yaml.safe_load((bench / "runtime-lock.yaml").read_text())
            errors = validator.validate_evidence(bench, lock)
        self.assertTrue(any("execution inputs" in error for error in errors))

    def test_evidence_rejects_fake_endpoint_and_source_substitution(self):
        with tempfile.TemporaryDirectory() as directory:
            bench = self._copy_reviewable_bench(directory)
            readiness_path = bench / "evidence/readiness.json"
            readiness = json.loads(readiness_path.read_text())
            readiness["endpoints"][0]["name"] = readiness["endpoints"][1]["name"]
            readiness_path.write_text(json.dumps(readiness))
            source_path = bench / "evidence/source-import.json"
            source = json.loads(source_path.read_text())
            source["repositories"][0]["name"] = "arbitrary_source"
            source_path.write_text(json.dumps(source))
            lock = yaml.safe_load((bench / "runtime-lock.yaml").read_text())
            errors = validator.validate_evidence(bench, lock)
        self.assertTrue(any("exact 009A boundary" in error for error in errors))
        self.assertTrue(any("exact locked source set" in error for error in errors))

    def test_evidence_rejects_wrong_image_and_map_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            bench = self._copy_reviewable_bench(directory)
            build_path = bench / "evidence/build-status.json"
            build = json.loads(build_path.read_text())
            build["image_digest"] = "sha256:" + "0" * 64
            build["map_sha256"] = "0" * 64
            build_path.write_text(json.dumps(build))
            lock = yaml.safe_load((bench / "runtime-lock.yaml").read_text())
            errors = validator.validate_evidence(bench, lock)
        self.assertTrue(any("wrong image digest" in error for error in errors))
        self.assertTrue(any("wrong map archive digest" in error for error in errors))

    def test_evidence_rejects_paired_fake_source_trees(self):
        with tempfile.TemporaryDirectory() as directory:
            bench = self._copy_reviewable_bench(directory)
            source_path = bench / "evidence/source-import.json"
            source = json.loads(source_path.read_text())
            for index, item in enumerate(source["repositories"], start=1):
                fake_tree = f"{index:040x}"
                item["expected_tree"] = fake_tree
                item["actual_tree"] = fake_tree
            source_path.write_text(json.dumps(source))
            lock = yaml.safe_load((bench / "runtime-lock.yaml").read_text())
            errors = validator.validate_evidence(bench, lock)
        self.assertTrue(any("false or incomplete" in error for error in errors))

    def test_evidence_rejects_invalid_image_id_and_unbound_repo_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            bench = self._copy_reviewable_bench(directory)
            for path in (bench / "evidence").glob("*.json"):
                if path.name == "readiness-ros.json":
                    continue
                document = json.loads(path.read_text())
                if document.get("image_id") is not None:
                    document["image_id"] = "sha256:not-a-digest"
                if path.name == "container-identity.json":
                    document["repo_digests"] = [
                        "example.invalid/image@sha256:" + "0" * 64
                    ]
                path.write_text(json.dumps(document))
            lock = yaml.safe_load((bench / "runtime-lock.yaml").read_text())
            errors = validator.validate_evidence(bench, lock)
        self.assertTrue(any("does not prove the locked ARM64 image" in error for error in errors))

    def test_evidence_rejects_impossible_receipt_timing(self):
        mutations = {
            "negative": lambda document: document.update(collection_window_seconds=-1),
            "non_finite": lambda document: document.update(
                collection_window_seconds=float("nan")
            ),
            "missing": lambda document: document.pop("collection_window_seconds", None),
            "out_of_window": lambda document: document["endpoints"][0].update(
                last_message_age_seconds=document["collection_window_seconds"] + 1
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                bench = self._copy_reviewable_bench(directory)
                readiness_path = bench / "evidence/readiness.json"
                readiness = json.loads(readiness_path.read_text())
                mutate(readiness)
                readiness_path.write_text(json.dumps(readiness))
                lock = yaml.safe_load((bench / "runtime-lock.yaml").read_text())
                errors = validator.validate_evidence(bench, lock)
                self.assertTrue(any("exact 009A boundary" in error for error in errors))

    def test_increments_preserve_distinct_sequenced_work(self):
        increments = yaml.safe_load((BENCH / "increments.yaml").read_text())
        by_id = {item["id"]: item for item in increments["increments"]}
        self.assertEqual(set(by_id), {f"INC-AEBS-009{suffix}" for suffix in "ABCDEFGHI"})
        self.assertEqual(by_id["INC-AEBS-009A"]["status"], "readiness_proven_no_scenario")
        self.assertEqual(
            by_id["INC-AEBS-009B"]["status"],
            "merged_replayable_nominal_moving_target_evidence",
        )
        self.assertEqual(by_id["INC-AEBS-009C"]["status"], "merged_partial_native_intervention_to_mrm_evidence")
        for suffix in "DEFGHI":
            self.assertEqual(by_id[f"INC-AEBS-009{suffix}"]["status"], "planned")
        boundaries = [tuple(item["acceptance_boundary"]) for item in by_id.values()]
        self.assertEqual(len(boundaries), len(set(boundaries)))

    def test_readmes_assign_009b_through_009i_scope_without_drift(self):
        readiness = (BENCH / "README.md").read_text(encoding="utf-8")
        nominal = (
            ROOT
            / "implementation/aebs-autoware-nominal-vehicle-target-bench/README.md"
        ).read_text(encoding="utf-8")
        for document in (readiness, nominal):
            with self.subTest(document=document[:40]):
                self.assertIn("INC-AEBS-009B owns nominal moving-vehicle-target evidence", document)
                self.assertIn("INC-AEBS-009C owns partial stationary-target native intervention-to-MRM/gate evidence", document)
                self.assertIn("INC-AEBS-009D owns conscious driver override", document)
                self.assertIn("INC-AEBS-009E owns non-activation and false-reaction scenarios", document)
                self.assertIn("INC-AEBS-009F owns failed and degraded operation", document)
                self.assertIn("INC-AEBS-009G owns pedestrian-target scenarios", document)
                self.assertIn("INC-AEBS-009H owns bicycle-target scenarios", document)
                self.assertIn("INC-AEBS-009I owns source-backed quantified criteria", document)

    def test_increment_contracts_cannot_be_erased(self):
        increments = yaml.safe_load((BENCH / "increments.yaml").read_text())
        self.assertEqual(validator.validate_increments(increments), [])

        weakened = copy.deepcopy(increments)
        for item in weakened["increments"]:
            if item["id"] != "INC-AEBS-009A":
                item["acceptance_boundary"] = ["placeholder"]
        errors = validator.validate_increments(weakened)
        for suffix in "BCDEFGHI":
            self.assertTrue(any(f"INC-AEBS-009{suffix} acceptance contract" in error for error in errors))

    def test_sysml_separates_realized_009a_from_planned_scenario_assets(self):
        model = (
            ROOT
            / "textual-notation-of-model/packages/features/aebs/aebs_simulation_deployment.sysml"
        ).read_text()
        realized = model.split("part def AEBSystem2SimulationAssets {", 1)[1].split(
            "part def AEBSystem2ToSystem1Connections {", 1
        )[0]
        self.assertIn("part readinessInputs : AEBReadinessInputs009A;", realized)
        self.assertNotIn("scenarioController", realized)
        self.assertNotIn("plannedTrajectory", realized)
        self.assertIn("part def PlannedAEBScenarioAssets009B009C {", model)
        planned = model.split("part def PlannedAEBScenarioAssets009B009C {", 1)[1].split(
            "part def SimplePlanningSimulatorTestDouble {", 1
        )[0]
        self.assertIn("part scenarioController : ScenarioController;", planned)

        system1 = model.split("part def AEBSystem1CandidateDeployment {", 1)[1].split(
            "part def AEBReadinessInputs009A {", 1
        )[0]
        self.assertIn("part def DeferredControlCommandGateAlternative {", model)
        self.assertNotIn("deferredControlCommandGate", system1)

    def test_pilot_artifacts_do_not_use_unqualified_009_ownership(self):
        artifacts = [
            ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-simulation-deployment.md",
            ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-simulation-deployment/README.md",
            ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-simulation-deployment/vss-simulation-realization.yaml",
            ROOT / "textual-notation-of-model/packages/features/aebs/aebs_simulation_deployment.sysml",
        ]
        for path in artifacts:
            with self.subTest(path=path):
                self.assertIsNone(re.search(r"INC-AEBS-009(?![ABC])", path.read_text()))

    def test_rejects_mutable_or_duplicate_source_identities(self):
        lock = yaml.safe_load((BENCH / "runtime-lock.yaml").read_text())
        mutable = copy.deepcopy(lock)
        mutable["sources"][0]["commit"] = "main"
        errors = validator.validate_runtime_lock(mutable)
        self.assertTrue(any("40-character" in error for error in errors))

        duplicate = copy.deepcopy(lock)
        duplicate["sources"].append(copy.deepcopy(duplicate["sources"][0]))
        errors = validator.validate_runtime_lock(duplicate)
        self.assertTrue(any("duplicate source identity" in error for error in errors))

    def test_map_and_oci_assets_are_exactly_pinned(self):
        lock = yaml.safe_load((BENCH / "runtime-lock.yaml").read_text())
        self.assertEqual(
            lock["container"]["index_digest"],
            "sha256:03f6e177d507504a26710041674a1386b1a63fe964870cb5ff48b5e59c635c17",
        )
        self.assertEqual(
            lock["container"]["platform_digest"],
            "sha256:0bcf71e1c7b45da5787f10def7cfcb2e26d5a25906d2af538ae7db167766136f",
        )
        self.assertEqual(
            lock["map"]["url"],
            "https://autoware-files.s3.us-west-2.amazonaws.com/maps/demos/sample-map-planning.zip",
        )
        self.assertEqual(
            lock["map"]["sha256"],
            "5536fce7bb8db7688fdf94ec004118b898637ad0d5b6175108b10989dd6e93b9",
        )
        self.assertEqual(validator.validate_runtime_lock(lock), [])

    def test_launch_directly_instantiates_aeb_without_invalid_remap(self):
        launch = (BENCH / "src/de4sdv_aebs_bench/launch/aebs_bench.launch.py").read_text()
        self.assertIn('package="autoware_autonomous_emergency_braking"', launch)
        self.assertIn('executable="autoware_autonomous_emergency_braking"', launch)
        self.assertNotIn("input_odometry", launch)
        self.assertNotIn("~/input/odometry", launch)

    def test_smoke_collects_readiness_inside_the_runtime_container(self):
        launch = (BENCH / "scripts/launch.sh").read_text()
        smoke = (BENCH / "scripts/smoke.sh").read_text()
        self.assertIn("de4sdv-aebs-009a-runtime", launch)
        self.assertIn("--name", launch)
        self.assertIn("docker exec", smoke)
        self.assertNotIn('docker compose -f "$BENCH/compose.yaml" run', smoke)

    def test_dds_uses_unprivileged_localhost_unicast(self):
        compose = (BENCH / "compose.yaml").read_text()
        cyclone = (BENCH / "cyclonedds.xml").read_text()
        self.assertIn("CYCLONEDDS_URI", compose)
        self.assertNotIn("NET_ADMIN", compose)
        self.assertIn('<Peer Address="localhost"', cyclone)
        self.assertIn("<AllowMulticast>false</AllowMulticast>", cyclone)

    def test_canonical_readiness_evidence_includes_typed_endpoint_receipts(self):
        smoke = (BENCH / "scripts/smoke.sh").read_text()
        metadata = (BENCH / "scripts/evidence_metadata.py").read_text()
        self.assertIn("--details", smoke)
        self.assertIn("--details", metadata)
        self.assertIn('details.get("endpoints")', metadata)
        self.assertIn('details.get("diagnostic_identity")', metadata)
        self.assertIn('"collection_window_seconds"', metadata)

    def test_readiness_requires_the_exact_aeb_diagnostic_identity(self):
        collector = (
            BENCH
            / "src/de4sdv_aebs_bench/de4sdv_aebs_bench/readiness_collector.py"
        ).read_text()
        self.assertIn(
            "autonomous_emergency_braking: aeb_emergency_stop", collector
        )
        self.assertIn("diagnostic_names", collector)
        self.assertIn('"diagnostic_identity"', collector)

    def test_source_import_json_records_each_expected_and_actual_revision(self):
        prepare = (BENCH / "scripts/prepare_workspace.sh").read_text()
        recorder = (BENCH / "scripts/record_source_heads.py").read_text()
        self.assertIn("record_source_heads.py", prepare)
        self.assertIn('"expected_revision"', recorder)
        self.assertIn('"actual_revision"', recorder)
        self.assertIn('"expected_tree"', recorder)
        self.assertIn('"actual_tree"', recorder)
        self.assertIn("status", recorder)
        self.assertIn("--porcelain", recorder)
        self.assertIn('"worktree_clean"', recorder)
        self.assertIn('"matches"', recorder)
        self.assertIn('"all_revisions_match"', recorder)

    def test_container_verifier_enforces_exact_arm64_manifest(self):
        verifier = (BENCH / "scripts/verify_container.py").read_text()
        self.assertIn('platform_digest != image["platform_digest"]', verifier)
        self.assertIn('"pull", "--platform", image["platform"]', verifier)
        self.assertIn('inspected_image["Architecture"]', verifier)
        self.assertIn('inspected_image["Os"]', verifier)

    def test_launch_reverifies_extracted_map_and_fails_clean_early_exit(self):
        launch = (BENCH / "scripts/launch.sh").read_text()
        verifier = (BENCH / "scripts/verify_map.py").read_text()
        self.assertIn('scripts/verify_map.py', launch)
        self.assertIn('status=1', launch)
        self.assertIn('extracted_sha256', verifier)
        self.assertIn('observed_files == expected_files', verifier)
        self.assertIn('map_files_verified', verifier)

    def test_runtime_evidence_is_reviewable_and_status_is_coherent(self):
        ignore = (BENCH / ".gitignore").read_text()
        lock = yaml.safe_load((BENCH / "runtime-lock.yaml").read_text())
        self.assertNotIn("evidence/*.json", ignore)
        self.assertEqual(lock["status"], "runtime_verified_009a_readiness_only")

    def test_source_recorder_rejects_dirty_worktree(self):
        with tempfile.TemporaryDirectory() as directory:
            bench = self._copy_reviewable_bench(directory)
            checkout = bench / "workspace/src/example"
            checkout.mkdir(parents=True)
            subprocess.run(["git", "init", "-q", str(checkout)], check=True)
            subprocess.run(["git", "-C", str(checkout), "config", "user.email", "test@example.invalid"], check=True)
            subprocess.run(["git", "-C", str(checkout), "config", "user.name", "Test"], check=True)
            tracked = checkout / "tracked.txt"
            tracked.write_text("locked\n")
            subprocess.run(["git", "-C", str(checkout), "add", "tracked.txt"], check=True)
            subprocess.run(["git", "-C", str(checkout), "commit", "-qm", "fixture"], check=True)
            revision = subprocess.run(
                ["git", "-C", str(checkout), "rev-parse", "HEAD"],
                check=True, capture_output=True, text=True,
            ).stdout.strip()
            (bench / "autoware-009a.repos").write_text(yaml.safe_dump({
                "repositories": {"example": {
                    "type": "git",
                    "url": "https://example.invalid/repo.git",
                    "version": revision,
                }}
            }))
            evidence = bench / "source.json"
            evidence.write_text('{"command_exit_status": 0}\n')
            tracked.write_text("tampered\n")
            result = subprocess.run([
                "python", str(BENCH / "scripts/record_source_heads.py"),
                str(bench), str(evidence),
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            recorded = json.loads(evidence.read_text())
            self.assertFalse(recorded["all_revisions_match"])
            self.assertFalse(recorded["repositories"][0]["worktree_clean"])

    def test_map_verifier_rejects_modified_extracted_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bench = self._copy_reviewable_bench(directory)
            cache = root / "cache"
            map_dir = cache / "map"
            map_dir.mkdir(parents=True)
            content = b"locked map bytes\n"
            expected = hashlib.sha256(content).hexdigest()
            (map_dir / "map.pcd").write_bytes(content + b"tamper")
            (bench / "runtime-lock.yaml").write_text(yaml.safe_dump({
                "container": {"index_digest": "sha256:" + "0" * 64},
                "map": {
                    "sha256": "0" * 64,
                    "extracted_directory": "map",
                    "extracted_sha256": {"map.pcd": expected},
                },
            }))
            result = subprocess.run([
                "python", str(BENCH / "scripts/verify_map.py"),
                "--bench", str(bench), "--cache", str(cache),
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            evidence = json.loads((bench / "evidence/map-runtime.json").read_text())
            self.assertFalse(evidence["map_files_verified"])

    def test_packaged_runtime_configs_match_authoritative_controls(self):
        authoritative = ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-simulation-deployment"
        packaged = BENCH / "src/de4sdv_aebs_bench/config"
        for filename in ("aebs.param.yaml", "diagnostic-graph.yaml"):
            with self.subTest(filename=filename):
                self.assertEqual(
                    (packaged / filename).read_bytes(),
                    (authoritative / filename).read_bytes(),
                )
        lock = yaml.safe_load((BENCH / "runtime-lock.yaml").read_text())
        controls = lock["map_parameter_controls"]
        for filename, control in controls.items():
            with self.subTest(filename=filename):
                digest = hashlib.sha256((packaged / filename).read_bytes()).hexdigest()
                self.assertEqual(digest, control["packaged_sha256"])
        self.assertEqual(
            controls["pointcloud_map_loader.param.yaml"]["disposition"],
            "pinned_copy_with_partial_loading_disabled_for_metadata_free_sample_map",
        )
        setup = (BENCH / "src/de4sdv_aebs_bench/setup.py").read_text()
        self.assertNotIn("resolve()", setup)
        self.assertNotIn("repo_root", setup)

    def test_readiness_requires_live_messages_across_the_full_chain(self):
        collector = (
            BENCH
            / "src/de4sdv_aebs_bench/de4sdv_aebs_bench/readiness_collector.py"
        ).read_text()
        lock = yaml.safe_load((BENCH / "runtime-lock.yaml").read_text())
        required = {
            "/map/vector_map",
            "/diagnostics",
            "/system/operation_mode/availability",
            "/system/fail_safe/mrm_state",
            "/system/emergency/control_cmd",
            "/control/command/control_cmd",
            "/localization/kinematic_state",
        }
        lock_names = {item["name"] for item in lock["readiness"]["endpoints"]}
        self.assertTrue(required <= lock_names)
        for topic in required:
            with self.subTest(topic=topic):
                self.assertIn(topic, collector)
        self.assertIn("get_message", collector)
        self.assertIn("create_subscription", collector)
        self.assertIn("received", collector)

    def test_build_selects_every_launched_exact_source_package(self):
        build = (BENCH / "scripts/build.sh").read_text()
        lock = yaml.safe_load((BENCH / "runtime-lock.yaml").read_text())
        packages = {
            "de4sdv_aebs_bench",
            "autoware_autonomous_emergency_braking",
            "autoware_diagnostic_graph_aggregator",
            "autoware_mrm_emergency_stop_operator",
            "autoware_mrm_handler",
            "autoware_simple_planning_simulator",
            "autoware_vehicle_cmd_gate",
            "tier4_map_launch",
        }
        self.assertIn("--packages-select", build)
        self.assertIn("-DBUILD_TESTING=OFF", build)
        self.assertEqual(set(lock["selected_ros_packages"]), packages)
        for package in packages:
            with self.subTest(package=package):
                self.assertIn(package, build)

    def test_nominal_fixture_only_supplies_typed_initialization_inputs(self):
        fixture = (
            BENCH
            / "src/de4sdv_aebs_bench/de4sdv_aebs_bench/nominal_fixture.py"
        ).read_text()
        for required in (
            "/initialpose3d",
            "/autoware/engage",
            "/api/operation_mode/state",
            "/system/operation_mode/state",
            "/autoware/state",
            "/control/trajectory_follower/control_cmd",
            "/control/shift_decider/gear_cmd",
            "/perception/obstacle_segmentation/pointcloud",
        ):
            with self.subTest(topic=required):
                self.assertIn(required, fixture)
        self.assertIn("PointField.FLOAT32", fixture)
        self.assertIn("cloud.point_step = 12", fixture)
        self.assertIn("AutowareState", fixture)
        manifest = (BENCH / "src/de4sdv_aebs_bench/package.xml").read_text()
        for dependency in ("autoware_adapi_v1_msgs", "autoware_control_msgs"):
            self.assertIn(f"<exec_depend>{dependency}</exec_depend>", manifest)

        for forbidden in (
            "/system/fail_safe/mrm_state",
            "/system/emergency/control_cmd",
            'create_publisher(Control, "/control/command/control_cmd"',
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, fixture)

    def test_launch_composes_the_inc_009a_runtime_chain(self):
        launch = (BENCH / "src/de4sdv_aebs_bench/launch/aebs_bench.launch.py").read_text()
        for package in (
            "tier4_map_launch",
            "autoware_diagnostic_graph_aggregator",
            "autoware_mrm_handler",
            "autoware_mrm_emergency_stop_operator",
            "autoware_vehicle_cmd_gate",
        ):
            with self.subTest(package=package):
                self.assertIn(package, launch)
        self.assertIn('"initial_engage_state": "true"', launch)
        self.assertIn('"vehicle_model_pkg": vehicle_info_share', launch)
        self.assertNotIn('"pointcloud_map_metadata_path": ""', launch)
        self.assertNotIn('"lanelet2_map_metadata_path": ""', launch)
        self.assertIn('package="autoware_vehicle_cmd_gate"', launch)
        self.assertNotIn("launch/vehicle_cmd_gate.launch.xml", launch)
        self.assertNotIn("mrm_emergency_stop_operator.launch.py", launch)
        self.assertIn("mrm_emergency_stop_operator.param.yaml", launch)
        self.assertIn("vehicle_info.param.yaml", launch)
        for remap in (
            'input/operation_mode", "/system/operation_mode/state',
            'input/kinematics", "/localization/kinematic_state',
            'input/acceleration", "/localization/acceleration',
            'output/operation_mode", "/control/vehicle_cmd_gate/operation_mode',
        ):
            self.assertIn(remap, launch)

    def test_workspace_bind_mount_source_is_precreated(self):
        self.assertTrue((BENCH / "workspace/.gitkeep").is_file())
        ignore = (BENCH / ".gitignore").read_text()
        self.assertIn("workspace/*", ignore)
        self.assertIn("!workspace/.gitkeep", ignore)

    def test_runtime_scripts_source_autoware_before_enabling_nounset(self):
        for name in ("prepare_workspace.sh", "build.sh", "launch.sh", "smoke.sh"):
            text = (BENCH / "scripts" / name).read_text()
            with self.subTest(script=name):
                self.assertNotIn(
                    "set -euo pipefail\n  source /opt/autoware/setup.bash",
                    text,
                )
                if name in ("launch.sh", "smoke.sh"):
                    self.assertIn(
                        "source /opt/autoware/setup.bash\n"
                        "  source /de4sdv/implementation/aebs-autoware-executable-bench/"
                        "workspace/install/setup.bash\n  set -u",
                        text,
                    )
                else:
                    self.assertIn(
                        "set -eo pipefail\n  source /opt/autoware/setup.bash\n  set -u",
                        text,
                    )

    def test_endpoints_match_inc_008_contract(self):
        lock = yaml.safe_load((BENCH / "runtime-lock.yaml").read_text())
        endpoints = {item["name"] for item in lock["readiness"]["endpoints"]}
        self.assertEqual(
            lock["readiness"]["diagnostic_identity"],
            {
                "node": "autonomous_emergency_braking",
                "task": "aeb_emergency_stop",
                "joined_key": "autonomous_emergency_braking: aeb_emergency_stop",
            },
        )
        self.assertTrue(
            {
                "/diagnostics",
                "/localization/kinematic_state",
                "/localization/acceleration",
                "/vehicle/status/steering_status",
                "/control/command/gear_cmd",
                "/system/mrm/emergency_stop/status",
            }.issubset(endpoints)
        )

    def test_evidence_schema_keeps_009a_claim_boundary(self):
        lock = yaml.safe_load((BENCH / "runtime-lock.yaml").read_text())
        fields = lock["evidence"]["status_fields"]
        self.assertEqual(fields, ["built", "launched", "ready", "scenario_executed"])
        self.assertFalse(lock["evidence"]["009a_required_values"]["scenario_executed"])
        forbidden = " ".join(lock["claim_boundaries"]).lower()
        for claim in ("braking", "safety", "compliance", "production readiness"):
            self.assertIn(claim, forbidden)


if __name__ == "__main__":
    unittest.main()
