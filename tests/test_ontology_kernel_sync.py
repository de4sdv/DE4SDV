"""Sync point 5 tests: basic-ontology YAML ↔ method kernel declaration gate.

Covers the gate behavior on the real repository state plus adversarial
probing of the checker functions per the declarative-artifact-testing skill.

Written as unittest.TestCase because CI runs
``python -m unittest discover -s tests``.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import check_model_sync  # noqa: E402

ONTOLOGY_YAML = ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"


def _load_ontology() -> dict:
    return yaml.safe_load(ONTOLOGY_YAML.read_text(encoding="utf-8"))


class OntologyKernelGateCleanRepo(unittest.TestCase):
    """The gate and the ontology YAML must be consistent on the current repo."""

    def test_ontology_kernel_gate_passes_on_clean_repo(self):
        errors: list[str] = []
        check_model_sync.check_ontology_kernel(errors)
        self.assertEqual(errors, [], "\n".join(errors))

    def test_every_ontology_class_has_a_kernel_mapping(self):
        """Every class must declare where its semantics live."""
        for name, spec in _load_ontology()["classes"].items():
            kernel = spec.get("kernel")
            self.assertIsInstance(
                kernel, dict, f"{name}: no kernel mapping"
            )
            has_declaration = "file" in kernel and "declaration" in kernel
            has_native = "native" in kernel
            has_external = "external" in kernel
            self.assertTrue(
                has_declaration or has_native or has_external,
                f"{name}: kernel mapping uses none of "
                f"file+declaration/native/external",
            )
            # Exactly one mapping style per class keeps the kernel block honest.
            styles = sum([has_declaration, has_native, has_external])
            self.assertEqual(
                styles, 1, f"{name}: {styles} mapping styles in one kernel block"
            )

    def test_kernel_mapping_files_exist(self):
        for name, spec in _load_ontology()["classes"].items():
            kernel = spec.get("kernel", {})
            if "file" in kernel:
                self.assertTrue(
                    (ROOT / kernel["file"]).exists(),
                    f"{name}: kernel file does not exist: {kernel['file']}",
                )

    def test_run_all_checks_includes_sync_point_five(self):
        """SP5 must be part of the aggregate gate, not an optional extra."""
        errors = check_model_sync.run_all_checks()
        self.assertFalse(
            any(e.startswith("[SP5]") for e in errors), "\n".join(errors)
        )


class DeclarationExistsProbing(unittest.TestCase):
    """Adversarial function-level probing of _declaration_exists."""

    def test_positive_and_negative(self):
        text = "package P {\n  part def Widget {\n  }\n}\n"
        self.assertTrue(
            check_model_sync._declaration_exists(text, "part def Widget")
        )
        self.assertFalse(
            check_model_sync._declaration_exists(text, "part def Gadget")
        )

    def test_ignores_comments(self):
        text = "/* part def FakeInComment */ part def Real {}"
        self.assertTrue(
            check_model_sync._declaration_exists(text, "part def Real")
        )
        self.assertFalse(
            check_model_sync._declaration_exists(
                text, "part def FakeInComment"
            )
        )

    def test_whole_word_no_prefix_false_positive(self):
        text = "part def EngineeringIncrement :> Base {}"
        self.assertTrue(
            check_model_sync._declaration_exists(
                text, "part def EngineeringIncrement"
            )
        )
        self.assertFalse(
            check_model_sync._declaration_exists(
                text, "part def EngineeringIncremen"
            )
        )

    def test_flexible_whitespace(self):
        text = "requirement def   StakeholderNeedCandidate\n{"
        self.assertTrue(
            check_model_sync._declaration_exists(
                text, "requirement def StakeholderNeedCandidate"
            )
        )


def _run_gate_with_tampered_yaml(mutate) -> list[str]:
    """Run check_ontology_kernel against a mutated copy of the ontology YAML."""
    doc = _load_ontology()
    mutate(doc)
    with tempfile.TemporaryDirectory() as tmp:
        tampered = Path(tmp) / "tampered-ontology.yaml"
        tampered.write_text(yaml.safe_dump(doc), encoding="utf-8")
        errors: list[str] = []
        with mock.patch.object(check_model_sync, "ONTOLOGY_YAML", tampered):
            check_model_sync.check_ontology_kernel(errors)
    return errors


class OntologyKernelGateFailureAttribution(unittest.TestCase):
    """Each failure mode must surface as an [SP5] error, not a silent pass."""

    def test_catches_renamed_kernel_declaration(self):
        def mutate(doc):
            doc["classes"]["EngineeringIncrement"]["kernel"]["declaration"] = (
                "part def NoLongerExists"
            )

        errors = _run_gate_with_tampered_yaml(mutate)
        self.assertTrue(
            any(
                "part def NoLongerExists" in e and "[SP5]" in e for e in errors
            ),
            errors,
        )

    def test_catches_missing_kernel_file(self):
        def mutate(doc):
            doc["classes"]["EngineeringIncrement"]["kernel"]["file"] = (
                "no/such/file.sysml"
            )

        errors = _run_gate_with_tampered_yaml(mutate)
        self.assertTrue(
            any("kernel file not found" in e for e in errors), errors
        )

    def test_catches_half_specified_kernel_mapping(self):
        def mutate(doc):
            del doc["classes"]["EngineeringIncrement"]["kernel"]["declaration"]

        errors = _run_gate_with_tampered_yaml(mutate)
        self.assertTrue(
            any("file: and declaration:" in e for e in errors), errors
        )

    def test_catches_missing_kernel_mapping(self):
        def mutate(doc):
            del doc["classes"]["EngineeringIncrement"]["kernel"]

        errors = _run_gate_with_tampered_yaml(mutate)
        self.assertTrue(
            any("missing kernel mapping" in e for e in errors), errors
        )

    def test_catches_invalid_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad-ontology.yaml"
            bad.write_text("classes: [unclosed\n  broken", encoding="utf-8")
            errors: list[str] = []
            with mock.patch.object(check_model_sync, "ONTOLOGY_YAML", bad):
                check_model_sync.check_ontology_kernel(errors)
        self.assertTrue(any("invalid YAML" in e for e in errors), errors)

    def test_catches_missing_yaml_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors: list[str] = []
            with mock.patch.object(
                check_model_sync, "ONTOLOGY_YAML", Path(tmp) / "absent.yaml"
            ):
                check_model_sync.check_ontology_kernel(errors)
        self.assertTrue(
            any("ontology YAML not found" in e for e in errors), errors
        )


class OntologyKernelSemanticsPins(unittest.TestCase):
    """Content pins tying the YAML to kernel semantics that the gate alone
    cannot see (it checks declaration existence, not the disjoint structure)."""

    def test_feature_common_capability_disjointness_is_symmetric(self):
        doc = _load_ontology()
        feature = doc["classes"]["Feature"]
        common = doc["classes"]["CommonCapability"]
        self.assertEqual(feature["disjointWith"], ["CommonCapability"])
        self.assertEqual(common["disjointWith"], ["Feature"])
        # Both must map to sibling ProductLineCharacteristic specializations.
        kernel_text = check_model_sync._read(ROOT / feature["kernel"]["file"])
        self.assertIn("ProductLineFeatureCandidate", feature["kernel"]["declaration"])
        self.assertIn(
            "CommonProductLineCapability", common["kernel"]["declaration"]
        )
        self.assertEqual(feature["kernel"]["file"], common["kernel"]["file"])
        for decl in (
            feature["kernel"]["declaration"],
            common["kernel"]["declaration"],
        ):
            self.assertTrue(
                check_model_sync._declaration_exists(kernel_text, decl), decl
            )

    def test_status_vocabulary_comes_from_upstream_not_local(self):
        """ADR 0009: no parallel local status enums in the ontology."""
        evidence_status = _load_ontology()["classes"]["EvidenceStatus"]
        self.assertIn(
            "external",
            evidence_status["kernel"],
            "EvidenceStatus must map to the upstream VVStatus enum, "
            "not a local vocabulary",
        )
        self.assertIn("VVStatus", evidence_status["kernel"]["external"])

    def test_schema_bumped_past_v0(self):
        """The synced schema version must not silently revert to v0."""
        self.assertEqual(_load_ontology()["schema"], "de4sdv.basic-ontology.v0.1")

    def test_method_context_kernel_declares_pinned_declarations(self):
        """All method-context-mapped classes resolve in that one file."""
        doc = _load_ontology()
        context_file = (
            "textual-notation-of-model/packages/methods/de4sdv/"
            "de4sdv_method_context.sysml"
        )
        kernel_text = check_model_sync._read(ROOT / context_file)
        mapped = [
            spec["kernel"]["declaration"]
            for spec in doc["classes"].values()
            if spec.get("kernel", {}).get("file") == context_file
        ]
        self.assertGreaterEqual(len(mapped), 5)
        for decl in mapped:
            self.assertTrue(
                check_model_sync._declaration_exists(kernel_text, decl), decl
            )


if __name__ == "__main__":
    unittest.main()
