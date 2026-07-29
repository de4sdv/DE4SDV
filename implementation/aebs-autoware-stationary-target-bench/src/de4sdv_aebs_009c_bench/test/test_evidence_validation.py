"""Adversarial tests for deterministic, independently replayed 009C evidence."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

BENCH = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = BENCH / "src" / "de4sdv_aebs_009c_bench"
sys.path[:0] = [str(BENCH / "scripts"), str(PACKAGE_ROOT)]

from de4sdv_aebs_009c_bench.scenario_contract import load_scenario_config  # noqa: E402
from de4sdv_aebs_009c_bench.scenario_evaluator import (  # noqa: E402
    Observation,
    ObservationKind,
    evaluate_scenario,
)
from evidence_document import (  # noqa: E402
    build_evidence_document,
    canonical_json_bytes,
    evaluation_to_json,
    observation_to_json,
    publish_validated_evidence,
    sha256_file,
    validate_raw_semantics,
    write_evidence_atomic,
)
from validate_scenario_evidence import (  # noqa: E402
    ValidationError,
    _live_provenance_fields,
    _repository_commit_is_ancestor,
    _repository_head_is_accepted,
    validate_evidence,
)

CONFIG = BENCH / "config" / "scenario-009c-aeb-mrm.yaml"
CLOCK_BOUNDARY = (
    "Order and causality use only collector monotonic receipt timestamps; preserved source "
    "stamps and host UTC are provenance only, and DDS/network order is not independently proved."
)

def obs(kind: ObservationKind, time: float, **payload: object) -> Observation:
    return Observation(kind, payload, time, source_stamp=f"ros:{time}", host_utc="2026-07-26T12:00:00Z")

def baseline(time: float) -> list[Observation]:
    return [
        obs(ObservationKind.DIAGNOSTIC, time, node="autonomous_emergency_braking", task="aeb_emergency_stop", level="OK"),
        obs(ObservationKind.AUTONOMOUS_AVAILABILITY, time, available=True),
        obs(ObservationKind.MRM_STATE, time, state="NORMAL", behavior="NONE"),
        obs(ObservationKind.EMERGENCY_OPERATOR_STATUS, time, state="AVAILABLE"),
        obs(ObservationKind.NOMINAL_COMMAND, time, speed_mps=5.0, acceleration_mps2=1.0),
        obs(ObservationKind.GATE_COMMAND, time, path="nominal", acceleration_mps2=1.0),
        obs(ObservationKind.ODOMETRY, time, speed_mps=5.0, acceleration_mps2=0.0),
    ]

def passing_observations() -> list[Observation]:
    items: list[Observation] = []
    for time in (0.0, 0.4, 0.8, 1.2, 1.6, 2.0):
        items += baseline(time)
    items += [
        obs(ObservationKind.TARGET_PUBLICATION, 2.1, identity="target-1", frame="map", x=6.0, y=0.0, yaw_rad=0.0),
        obs(
            ObservationKind.AEB_INTERVENTION,
            2.2,
            message="[AEB]: Emergency Brake",
            rss_distance_m=6.1,
            object_distance_m=5.8,
            object_speed_mps=0.0,
        ),
        obs(ObservationKind.AUTONOMOUS_AVAILABILITY, 2.3, available=False),
        obs(ObservationKind.MRM_STATE, 2.4, state="MRM_OPERATING", behavior="EMERGENCY_STOP"),
        obs(ObservationKind.EMERGENCY_OPERATOR_STATUS, 2.45, state="OPERATING"),
        obs(ObservationKind.EMERGENCY_COMMAND, 2.5, speed_mps=0.0, acceleration_mps2=-1.2),
        obs(ObservationKind.NOMINAL_COMMAND, 2.55, speed_mps=5.0, acceleration_mps2=0.4),
        obs(ObservationKind.ODOMETRY, 2.56, speed_mps=4.8, acceleration_mps2=0.0),
        obs(ObservationKind.GATE_EMERGENCY_STATUS, 2.58, emergency=True),
        obs(ObservationKind.GATE_COMMAND, 2.6, path="emergency", acceleration_mps2=-0.7),
        obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.2, acceleration_mps2=-0.2),
    ]
    return items

class EvidenceValidationTests(unittest.TestCase):
    def test_squash_delivered_reviewed_head_accepts_retained_run_ancestor(self) -> None:
        repository = BENCH.parents[1]
        relation = {
            "pull_request": 66,
            "retained_run_head": "a6234b572659ad052ecd647585552ded98bca569",
            "reviewed_head": "871ef95bbdf3b865d5761d692065674fc0b4e196",
            "delivery_commit": "81e043386251118b302bafbed91922f8fa821522",
        }
        live_head = subprocess.check_output(
            ["git", "-C", repository, "rev-parse", "HEAD"], text=True
        ).strip()
        self.assertTrue(
            _repository_head_is_accepted(
                repository, relation["retained_run_head"], live_head, relation
            )
        )
        unrelated = subprocess.check_output(
            ["git", "-C", repository, "rev-parse", "6dd6653^{commit}"], text=True
        ).strip()
        self.assertFalse(
            _repository_head_is_accepted(repository, unrelated, live_head, relation)
        )

    def test_recorded_run_base_may_precede_reviewing_commit(self) -> None:
        repository = Path(self.temp.name) / "ancestry-repository"
        repository.mkdir()
        subprocess.run(["git", "init", "-q", repository], check=True)
        subprocess.run(
            ["git", "-C", repository, "config", "user.name", "de4sdv"],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                repository,
                "config",
                "user.email",
                "de4sdv@users.noreply.github.com",
            ],
            check=True,
        )
        marker = repository / "marker"
        marker.write_text("run base\n", encoding="utf-8")
        subprocess.run(["git", "-C", repository, "add", "marker"], check=True)
        subprocess.run(
            ["git", "-C", repository, "commit", "-qm", "run base"], check=True
        )
        run_base = subprocess.check_output(
            ["git", "-C", repository, "rev-parse", "HEAD"], text=True
        ).strip()
        marker.write_text("review commit\n", encoding="utf-8")
        subprocess.run(["git", "-C", repository, "commit", "-qam", "review"], check=True)
        review_head = subprocess.check_output(
            ["git", "-C", repository, "rev-parse", "HEAD"], text=True
        ).strip()

        self.assertTrue(
            _repository_commit_is_ancestor(repository, run_base, review_head)
        )
        self.assertFalse(
            _repository_commit_is_ancestor(repository, review_head, run_base)
        )

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.bench = Path(self.temp.name) / "bench"
        (self.bench / "evidence" / "009c").mkdir(parents=True)
        self.artifact = self.bench / "evidence" / "009c" / "observer.log"
        self.artifact.write_bytes(b"observer output\n")
        self.provenance = {
            "captured_utc": "2026-07-26T12:00:01Z",
            "host_arch": "aarch64",
            "repository_head": "a" * 40,
            "execution_manifest_sha256": "b" * 64,
            "runtime_lock_sha256": "c" * 64,
            "inherited_009a": {
                "execution_manifest_sha256": "d" * 64,
                "runtime_lock_sha256": "e" * 64,
            },
            "image_digest": "sha256:" + "f" * 64,
            "map_digest": "sha256:" + "1" * 64,
            "command_exit_code": 0,
        }
        config = load_scenario_config(CONFIG)
        observations = passing_observations()
        raw = {
            "collector_id": "de4sdv.scenario_observer.v1",
            "monotonic_start_s": 0.0,
            "monotonic_end_s": 3.0,
            "clock_boundary": CLOCK_BOUNDARY,
            "observations": [observation_to_json(item) for item in observations],
            "evaluator_result": evaluation_to_json(
                evaluate_scenario(config, observations)
            ),
            "activation": {
                "request_time_s": 2.01,
                "response_time_s": 2.02,
                "status": "succeeded",
                "response_message": "target injected",
            },
            "errors": [],
            "terminal_reason": "pass_observed_chain",
            "command_exit": 0,
            "limits": {
                "timeout_s": 30.0,
                "deadline_s": 30.0,
                "observation_cap": 30000,
                "error_cap": 256,
            },
        }
        self.raw = raw
        self.raw_artifact = self.bench / "evidence" / "009c" / "observer-raw.json"
        self.raw_artifact.write_bytes(canonical_json_bytes(raw))
        self.metadata_artifact = self.bench / "evidence" / "009c" / "run-metadata.json"
        self.metadata_artifact.write_bytes(canonical_json_bytes({
            "observer_exit_code": 0,
            "raw_output": "evidence/009c/observer-raw.json",
        }))
        self.launch_artifact = self.bench / "evidence" / "009c" / "launch.log"
        self.launch_artifact.write_text("launch output\n", encoding="utf-8")
        self.map_artifact = self.bench / "evidence" / "009c" / "map-runtime.json"
        authoritative_lock = yaml.safe_load(
            (BENCH / "runtime-lock.yaml").read_text(encoding="utf-8")
        )
        (self.bench / "runtime-lock.yaml").write_text(
            yaml.safe_dump({"map": authoritative_lock["map"]}), encoding="utf-8"
        )
        self.map_runtime = {
            "command_exit_status": 0,
            "error": None,
            "execution_manifest_sha256": self.provenance["execution_manifest_sha256"],
            "extracted_sha256": copy.deepcopy(
                authoritative_lock["map"]["extracted_sha256"]
            ),
            "host_architecture": self.provenance["host_arch"],
            "image_digest": self.provenance["image_digest"],
            "image_id": None,
            "lock_sha256": self.provenance["runtime_lock_sha256"],
            "map_files_verified": True,
            "map_sha256": self.provenance["map_digest"].removeprefix("sha256:"),
            "repository_head": self.provenance["repository_head"],
            "utc_time": "2026-07-26T12:00:00Z",
        }
        self.map_artifact.write_bytes(canonical_json_bytes(self.map_runtime))
        artifacts = {
            "observer_log": {
                "path": "evidence/009c/observer.log",
                "sha256": sha256_file(self.artifact),
            },
            "observer_raw": {
                "path": "evidence/009c/observer-raw.json",
                "sha256": sha256_file(self.raw_artifact),
            },
            "run_metadata": {
                "path": "evidence/009c/run-metadata.json",
                "sha256": sha256_file(self.metadata_artifact),
            },
            "launch_log": {
                "path": "evidence/009c/launch.log",
                "sha256": sha256_file(self.launch_artifact),
            },
            "map_runtime": {
                "path": "evidence/009c/map-runtime.json",
                "sha256": sha256_file(self.map_artifact),
            },
        }
        self.document = build_evidence_document(
            raw, config, self.provenance, artifacts,
        )
        self.path = self.bench / "evidence" / "009c" / "scenario-evidence.json"
        self.write(self.document)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, document: object) -> None:
        self.path.write_bytes(canonical_json_bytes(document))

    def validate(self) -> None:
        validate_evidence(
            self.path, bench_root=self.bench, scenario_config=CONFIG,
            expected_provenance=self.provenance,
        )

    def test_synthetic_pass_is_deterministic_and_replay_accepted(self) -> None:
        self.validate()
        first = canonical_json_bytes(self.document)
        second = canonical_json_bytes(copy.deepcopy(self.document))
        self.assertEqual(first, second)
        self.assertEqual(self.document["evaluation"]["outcome"], "pass_observed_chain")

    def test_rejects_target_publication_before_activation_request(self) -> None:
        changed = copy.deepcopy(self.raw)
        changed["activation"]["request_time_s"] = 2.11
        changed["activation"]["response_time_s"] = 2.12

        with self.assertRaisesRegex(
            ValueError, "target publication precedes activation request"
        ):
            validate_raw_semantics(
                changed,
                load_scenario_config(CONFIG),
                changed["evaluator_result"],
            )

    def test_relative_bench_root_is_normalized_for_independent_replay(self) -> None:
        previous = Path.cwd()
        try:
            os.chdir(self.bench)
            validate_evidence(
                self.path,
                bench_root=".",
                scenario_config=CONFIG,
                expected_provenance=self.provenance,
            )
        finally:
            os.chdir(previous)

    def test_live_image_provenance_uses_executed_index_digest(self) -> None:
        lock = yaml.safe_load(
            (BENCH / "runtime-lock.yaml").read_text(encoding="utf-8")
        )
        live = _live_provenance_fields(BENCH)
        self.assertEqual(live["image_digest"], lock["container"]["index_digest"])

    def test_rejects_verdict_observation_index_and_clock_mutations(self) -> None:
        mutations = (
            lambda d: d["evaluation"].__setitem__("outcome", "fail_scenario"),
            lambda d: d["collection"]["observations"][0]["payload"].__setitem__("level", "WARN"),
            lambda d: d["evaluation"]["accepted_events"][0].__setitem__("observation_index", 1),
            lambda d: d["collection"].__setitem__("monotonic_start_s", 0.1),
            lambda d: d["collection"]["observations"][1].__setitem__("receipt_monotonic_s", -0.1),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                changed = copy.deepcopy(self.document)
                mutate(changed)
                self.write(changed)
                with self.assertRaises(ValidationError):
                    self.validate()

    def test_rejects_artifact_byte_hash_provenance_and_unsafe_paths(self) -> None:
        self.artifact.write_bytes(b"changed")
        with self.assertRaises(ValidationError):
            self.validate()
        self.artifact.write_bytes(b"observer output\n")
        changed = copy.deepcopy(self.document)
        changed["artifacts"]["observer_log"]["sha256"] = "0" * 64
        self.write(changed)
        with self.assertRaises(ValidationError):
            self.validate()
        for path in ("../escape", "/absolute"):
            changed = copy.deepcopy(self.document)
            changed["artifacts"]["observer_log"]["path"] = path
            self.write(changed)
            with self.assertRaises(ValidationError):
                self.validate()
        changed = copy.deepcopy(self.document)
        changed["provenance"]["repository_head"] = "9" * 40
        self.write(changed)
        with self.assertRaises(ValidationError):
            self.validate()

    def test_rejects_incomplete_or_open_artifact_set(self) -> None:
        for mutation in ("missing", "extra"):
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(self.document)
                if mutation == "missing":
                    changed["artifacts"].pop("launch_log")
                else:
                    changed["artifacts"]["extra"] = copy.deepcopy(
                        changed["artifacts"]["observer_log"]
                    )
                self.write(changed)
                with self.assertRaises(ValidationError):
                    self.validate()

    def test_rejects_symlink_artifact(self) -> None:
        target = self.bench / "real.log"
        target.write_text("observer output\n", encoding="utf-8")
        self.artifact.unlink()
        os.symlink(target, self.artifact)
        with self.assertRaises(ValidationError):
            self.validate()

    def test_rejects_digest_shaped_map_substitution_even_when_rehashed(self) -> None:
        changed_runtime = copy.deepcopy(self.map_runtime)
        changed_runtime["extracted_sha256"]["lanelet2_map.osm"] = "0" * 64
        self.map_artifact.write_bytes(canonical_json_bytes(changed_runtime))
        changed = copy.deepcopy(self.document)
        changed["artifacts"]["map_runtime"]["sha256"] = sha256_file(self.map_artifact)
        self.write(changed)
        with self.assertRaisesRegex(ValidationError, "do not match runtime lock"):
            self.validate()

    def test_rejects_hardlink_alias_across_artifact_roles(self) -> None:
        self.launch_artifact.unlink()
        os.link(self.artifact, self.launch_artifact)
        changed = copy.deepcopy(self.document)
        changed["artifacts"]["launch_log"]["sha256"] = sha256_file(
            self.launch_artifact
        )
        self.write(changed)
        with self.assertRaisesRegex(ValidationError, "distinct files"):
            self.validate()

    def test_parser_rejects_duplicate_keys_and_nonfinite_numbers(self) -> None:
        self.path.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "duplicate"):
            self.validate()
        text = canonical_json_bytes(self.document).decode().replace('"monotonic_start_s":0.0', '"monotonic_start_s":NaN')
        self.path.write_text(text, encoding="utf-8")
        with self.assertRaises(ValidationError):
            self.validate()

    def test_atomic_writer_rejects_outside_symlink_and_preserves_existing(self) -> None:
        canonical = self.bench / "evidence" / "009c" / "canonical.json"
        canonical.write_text("old", encoding="utf-8")
        with self.assertRaises(ValueError):
            write_evidence_atomic(self.document, self.bench / "outside.json", self.bench)
        link = self.bench / "evidence" / "009c" / "link.json"
        os.symlink(canonical, link)
        with self.assertRaises(ValueError):
            write_evidence_atomic(self.document, link, self.bench)
        self.assertEqual(canonical.read_text(encoding="utf-8"), "old")

    def test_builder_rejects_mutated_collector_semantics(self) -> None:
        config = load_scenario_config(CONFIG)
        mutations = (
            lambda r: r.__setitem__("collector_id", "other"),
            lambda r: r.__setitem__("clock_boundary", "wall clock"),
            lambda r: r["activation"].__setitem__("status", "pending"),
            lambda r: r["limits"].__setitem__("deadline_s", 31.0),
            lambda r: r["limits"].__setitem__("error_cap", 255),
            lambda r: r.__setitem__("terminal_reason", "timeout"),
            lambda r: r.__setitem__("errors", ["collector failure"]),
            lambda r: r.__setitem__("command_exit", 1),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                raw = copy.deepcopy(self.raw)
                mutate(raw)
                with self.assertRaises((TypeError, ValueError)):
                    build_evidence_document(raw, config, self.provenance, {})

    def test_validator_rejects_canonical_collector_contract_divergence(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["collector_contract"]["activation"]["response_message"] = "forged"
        self.write(changed)
        with self.assertRaisesRegex(ValidationError, "differs"):
            self.validate()

    def test_publication_rejects_symlink_and_directory_canonical(self) -> None:
        candidate = self.bench / "evidence" / "009c" / "candidate.json"
        candidate.write_text("candidate", encoding="utf-8")
        target = self.bench / "evidence" / "009c" / "published.json"
        outside = self.bench / "outside.json"
        outside.write_text("outside", encoding="utf-8")
        os.symlink(outside, target)
        with self.assertRaises(ValueError):
            publish_validated_evidence(candidate, target, self.bench)
        self.assertEqual(outside.read_text(encoding="utf-8"), "outside")
        target.unlink()
        target.mkdir()
        with self.assertRaises(ValueError):
            publish_validated_evidence(candidate, target, self.bench)
        self.assertTrue(candidate.is_file())

    def test_run_wrapper_has_fail_closed_observer_and_validation_contract(self) -> None:
        wrapper = (BENCH / "scripts" / "run_scenario.sh").read_text(encoding="utf-8")
        self.assertIn("set -euo pipefail", wrapper)
        self.assertIn("trap cleanup EXIT", wrapper)
        self.assertIn('docker exec --user "$(id -u):$(id -g)" --env HOME=/home/aw "$CONTAINER"', wrapper)
        self.assertIn("scenario_observer", wrapper)
        self.assertIn('OBSERVER_LOG="$STAGE/observer.log"', wrapper)
        self.assertIn('exec {observer_fd}>"$OBSERVER_LOG"', wrapper)
        self.assertIn('timeout --signal=TERM "$1"', wrapper)
        self.assertIn("--ros-args", wrapper)
        self.assertIn("scenario_config:=", wrapper)
        self.assertIn("raw_output:=", wrapper)
        self.assertIn("timeout_s:=", wrapper)
        self.assertIn(
            "workspace/install/de4sdv_aebs_009c_bench/share", wrapper
        )
        self.assertIn("SUPERVISOR_TIMEOUT", wrapper)
        self.assertIn('RUNS="$EVIDENCE/runs"', wrapper)
        self.assertNotIn('mkdir -p "$RUNS"', wrapper)
        self.assertIn('mv -T -- "$STAGE" "$FINAL"', wrapper)
        self.assertIn("stop_runtime", wrapper)
        self.assertIn("native geometry/process failure detected", wrapper)
        self.assertIn("QH[0-9]+ qhull input error", wrapper)
        self.assertIn("process has died", wrapper)
        self.assertIn("Traceback \\(most recent call last\\)", wrapper)
        self.assertLess(
            wrapper.index("stop_runtime\nif"), wrapper.index("hashlib,json,pathlib")
        )
        self.assertIn("validate_scenario_evidence.py", wrapper)
        self.assertLess(
            wrapper.rindex("validate_scenario_evidence.py"),
            wrapper.index("publish_validated_evidence"),
        )
        self.assertNotIn('mv -f -- "$STAGED" "$CANONICAL"', wrapper)
        self.assertNotIn("eval ", wrapper)

if __name__ == "__main__":
    unittest.main()
